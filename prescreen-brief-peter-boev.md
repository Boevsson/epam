# AI-Powered Financial Document Analysis Service


## Overview
NovaBridge Capital is a boutique investment advisory firm whose analysts provide clients with deep insights derived from public company financial disclosures. Currently, analysts manually read through hundreds of pages of SEC 10-K filings to identify key risk factors, financial performance indicators, and strategic shifts. This process is time-consuming, laborious, and prone to human error, limiting the number of companies they can cover effectively. To scale their operations and improve the quality of their analysis, NovaBridge wants to build an internal tool that allows analysts to ask natural language questions about a company's filings and receive concise, accurate, and verifiable answers.

Your task is to build a prototype of this AI-powered document analysis service. You will create a full-stack application consisting of a Python backend and a simple web frontend. The backend will ingest a small corpus of 10-K filings (provided as PDFs), process them, and expose an API for querying. A key requirement is to implement a hybrid search mechanism for retrieval, combining traditional keyword-based search with modern semantic (vector) search to ensure both precision and contextual relevance. The service should then use a large language model (LLM) to synthesize an answer based on the retrieved information, citing its sources.

The frontend will be a minimal but functional user interface where an analyst can type a question, submit it to the backend, and view the generated answer along with the source passages from the original documents. The focus is on the system's architecture, the quality of the hybrid search implementation, and the end-to-end functionality. The UI does not need to be visually polished.

## Deliverables
- A public GitHub repository or a single GitHub Gist URL containing your complete solution.
- A Python-based backend service that ingests documents and exposes a question-answering API.
- A simple frontend web application (React or plain HTML/CSS/JS) that consumes the backend API.
- A `README.md` file explaining your design decisions, trade-offs, a brief description of how your hybrid search works, and clear instructions on how to build and run the application.
- Your AI assistant conversation logs (e.g., Copilot Chat export, Claude conversation history) committed to the repository, as described in the notes below.

## Suggested tools / libraries
- Backend: FastAPI, Flask
- AI/ML: LangChain, LlamaIndex, Sentence-Transformers (for local embeddings)
- Search: FAISS/ChromaDB (for vector search), BM25/Whoosh (for keyword search)
- Frontend: React + Vite, Next.js, or plain HTML/CSS/JavaScript with the `fetch` API
- Operations: Docker, Docker Compose

## On AI assistants & follow-up
- We expect and encourage you to use documentation, open-source libraries, and AI assistants. Your value is in your judgment, not memorization.
- Be prepared to walk us through any part of your code and explain the design choices and trade-offs you made during the follow-up interview.
- We will ask deep-dive questions about your system's architecture, potential failure modes, and how you would scale or productionize your prototype.
- You must commit your AI assistant conversation logs to your repository (e.g., VS Code's 'Export Chat' for GitHub Copilot, a PDF/text export from Claude/ChatGPT, etc.). In your README, please add a short note on which tools you used and for what parts of the task.

## How to submit
Reply to this email with **one** public GitHub repository or gist URL containing your solution.

<!-- AI-EVALUATOR:PRESCREEN-META {"language":"Python","dueDays":10,"timeBudgetHours":10} -->