import { useEffect, useState } from "react";
import { api, type Answer, type Filing, type Filters, type Readiness } from "./api";
import { AnswerView } from "./components/AnswerView";
import { QuestionForm } from "./components/QuestionForm";
import { SourceList } from "./components/SourceList";

export default function App() {
  const [filings, setFilings] = useState<Filing[]>([]);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [showRetrieval, setShowRetrieval] = useState(false);

  useEffect(() => {
    api.ready().then(setReadiness).catch((reason: Error) => setError(reason.message));
    api.filings().then(setFilings).catch(() => setFilings([]));
  }, []);

  async function ask(question: string, filters: Filters) {
    setBusy(true);
    setError(null);
    setSelected(null);
    try {
      setAnswer(await api.ask(question, filters));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      setAnswer(null);
    } finally {
      setBusy(false);
    }
  }

  function selectCitation(passageId: string) {
    setSelected(passageId);
    document.getElementById(`source-${passageId}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <main>
      <header className="app-header">
        <h1>NovaBridge Filings Q&amp;A</h1>
        {readiness && (
          <span className="readiness">
            {filings.length} filings indexed ·{" "}
            {readiness.answer_generator === "claude" ? "AI answers with citations" : "passages only (no API key)"}
          </span>
        )}
      </header>
      <QuestionForm filings={filings} busy={busy} onAsk={ask} />
      {error && <p className="error">{error}</p>}
      {answer && (
        <>
          <AnswerView answer={answer} onSelectCitation={selectCitation} />
          <label className="toggle">
            <input type="checkbox" checked={showRetrieval} onChange={(event) => setShowRetrieval(event.target.checked)} />
            Show retrieval details (BM25 rank, dense rank, fused score)
          </label>
          <SourceList answer={answer} selected={selected} showRetrieval={showRetrieval} />
        </>
      )}
    </main>
  );
}
