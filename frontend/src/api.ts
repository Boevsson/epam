// Typed client for the backend API (mirrors backend/src/filings_qa/entrypoints/http/schemas.py).

export interface Pages {
  start: number;
  end: number;
}

export interface Source {
  passage_id: string;
  filing_id: string;
  label: string;
  company: string;
  ticker: string;
  fiscal_year: number;
  item: string;
  item_heading: string;
  pages: Pages;
  document_url: string;
}

export interface Evidence extends Source {
  text: string;
  sentences: string[];
  retrieval: { fused_score: number; ranks: Record<string, { rank: number; score: number }> };
}

export interface Citation extends Source {
  id: string;
  quote: string;
}

export type Status = "grounded" | "partially_grounded" | "insufficient_evidence" | "extractive_fallback";

export interface Scope {
  tickers: string[];
  fiscal_years: number[];
  items: string[];
  source: "explicit" | "detected" | "none";
}

export interface Answer {
  question: string;
  status: Status;
  segments: { text: string; citation_ids: string[] }[];
  citations: Citation[];
  evidence: Evidence[];
  scope: Scope;
  meta: {
    generator: string;
    model: string | null;
    notice: string | null;
    coverage: number;
    timings_ms: Record<string, number>;
  };
}

export interface Filing {
  filing_id: string;
  company: string;
  ticker: string;
  fiscal_year: number;
  page_count: number;
  passage_count: number;
  document_url: string;
}

export interface Filters {
  tickers: string[];
  fiscal_years: number[];
  items: string[];
}

export interface Readiness {
  status: string;
  snapshot: string;
  answer_generator: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { "content-type": "application/json" }, ...init });
  if (!response.ok) {
    // Errors are RFC 9457 problem details: { title, status, detail }.
    const problem = await response.json().catch(() => null);
    throw new Error(problem?.detail ?? problem?.title ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  ask: (question: string, filters: Filters) =>
    request<Answer>("/api/v1/questions", { method: "POST", body: JSON.stringify({ question, filters }) }),
  filings: () => request<Filing[]>("/api/v1/filings"),
  ready: () => request<Readiness>("/ready"),
};
