"""FastAPI application: routes, error mapping (RFC 9457 problem details) and lifecycle.

Handlers are plain ``def`` functions on purpose: query embedding is CPU-bound, and FastAPI runs sync handlers
in a thread pool instead of blocking the event loop.
"""

import logging
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from filings_qa.entrypoints.http.mapping import API_PREFIX, document_url, to_answer, to_scope, to_search
from filings_qa.entrypoints.http.schemas import AnswerOut, FilingOut, QuestionIn, ReadyOut, SearchIn, SearchOut
from filings_qa.research.application.ask_question import AskQuestionCommand
from filings_qa.research.application.ports import IndexUnavailableError
from filings_qa.research.application.search_passages import SearchCommand, UnknownSearchModeError
from filings_qa.research.application.services import ResearchServices
from filings_qa.shared_kernel.errors import InvalidValueError
from filings_qa.shared_kernel.values import FilingId

logger = logging.getLogger(__name__)
PROBLEM_JSON = "application/problem+json"


class ServiceNotReadyError(Exception):
    """The index snapshot could not be loaded, so questions cannot be answered yet."""


class DocumentNotFoundError(Exception):
    """No source PDF is known for the requested filing."""


def problem(status: int, title: str, detail: str) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def loaded_services(request: Request) -> ResearchServices:
    loaded: ResearchServices | None = request.app.state.services
    if loaded is None:
        raise ServiceNotReadyError(request.app.state.not_ready_reason)
    return loaded


Services = Annotated[ResearchServices, Depends(loaded_services)]


def create_app(services_factory: Callable[[], ResearchServices], *, cors_origins: Sequence[str] = ()) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.services, app.state.not_ready_reason = None, "starting"
        try:
            app.state.services = await run_in_threadpool(services_factory)  # loads the snapshot and models once
            app.state.not_ready_reason = None
        except IndexUnavailableError as error:
            logger.warning("service not ready: %s", error)
            app.state.not_ready_reason = str(error)
        yield

    app = FastAPI(
        title="NovaBridge Filings Q&A",
        version="1.0.0",
        summary="Questions about SEC 10-K filings, answered with page-level citations.",
        lifespan=lifespan,
    )
    if cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(cors_origins), allow_methods=["GET", "POST"])

    @app.exception_handler(InvalidValueError)
    def invalid_value(_: Request, error: InvalidValueError) -> JSONResponse:
        return problem(422, "Invalid request", str(error))

    @app.exception_handler(UnknownSearchModeError)
    def unknown_mode(_: Request, error: UnknownSearchModeError) -> JSONResponse:
        return problem(422, "Unknown search mode", str(error))

    @app.exception_handler(RequestValidationError)
    def invalid_body(_: Request, error: RequestValidationError) -> JSONResponse:
        detail = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors())
        return problem(422, "Invalid request body", detail)

    @app.exception_handler(ServiceNotReadyError)
    def not_ready(_: Request, error: ServiceNotReadyError) -> JSONResponse:
        return problem(503, "Service not ready", str(error))

    @app.exception_handler(DocumentNotFoundError)
    def no_document(_: Request, error: DocumentNotFoundError) -> JSONResponse:
        return problem(404, "Document not found", str(error))

    @app.get("/health", tags=["operations"])
    def health() -> dict[str, str]:
        """Liveness: the process is up."""
        return {"status": "ok"}

    @app.get("/ready", tags=["operations"])
    def ready(svc: Services) -> ReadyOut:
        """Readiness: the index snapshot and models are loaded."""
        return ReadyOut(status="ready", snapshot=svc.snapshot_version, answer_generator=svc.answer_generator)

    @app.post(f"{API_PREFIX}/questions", tags=["research"])
    def ask(body: QuestionIn, svc: Services) -> AnswerOut:
        """Answer a question with citations to the filings, plus the evidence and how it was retrieved."""
        return to_answer(svc.ask(AskQuestionCommand(body.question, to_scope(body.filters))))

    @app.post(f"{API_PREFIX}/search", tags=["research"])
    def search(body: SearchIn, svc: Services) -> SearchOut:
        """Retrieval only, with the hybrid, keyword or semantic retriever: shows how each ranks passages."""
        return to_search(svc.search(SearchCommand(body.query, body.mode, body.limit, to_scope(body.filters))))

    @app.get(f"{API_PREFIX}/filings", tags=["filings"])
    def filings(svc: Services) -> list[FilingOut]:
        """The filings in the live index."""
        return [
            FilingOut(
                filing_id=f.filing_id,
                company=f.company,
                ticker=str(f.ticker),
                fiscal_year=f.fiscal_year.value,
                page_count=f.page_count,
                passage_count=f.passage_count,
                document_url=document_url(f.filing_id),
            )
            for f in svc.list_filings()
        ]

    @app.get(f"{API_PREFIX}/filings/{{filing_id}}/document", tags=["filings"], response_class=FileResponse)
    def document(filing_id: str, svc: Services) -> FileResponse:
        """The original PDF, shown inline; append #page=N to open it at a cited page."""
        path = svc.documents.path_for(FilingId(filing_id))
        if path is None:
            raise DocumentNotFoundError(f"no source document for filing {filing_id}")
        return FileResponse(path, media_type="application/pdf", filename=path.name, content_disposition_type="inline")

    return app
