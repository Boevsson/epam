import { useState, type FormEvent } from "react";
import type { Filing, Filters } from "../api";

const SECTIONS: [string, string][] = [
  ["1", "Item 1 · Business"],
  ["1A", "Item 1A · Risk Factors"],
  ["7", "Item 7 · MD&A"],
  ["7A", "Item 7A · Market Risk"],
  ["8", "Item 8 · Financial Statements"],
];

const EXAMPLES = [
  "What drove revenue change as of FY2022 for AMD?",
  "Who are the primary customers of Boeing as of FY2022?",
  "What are the geographies that PepsiCo primarily operates in as of FY2022?",
  "How did American Express's effective tax rate change between FY2021 and FY2022?",
  "What are the main risks Pfizer highlights about drug pricing?",
];

interface Props {
  filings: Filing[];
  busy: boolean;
  onAsk: (question: string, filters: Filters) => void;
}

export function QuestionForm({ filings, busy, onAsk }: Props) {
  const [question, setQuestion] = useState("");
  const [ticker, setTicker] = useState("");
  const [year, setYear] = useState("");
  const [item, setItem] = useState("");

  const companies = [...new Map(filings.map((f) => [f.ticker, f.company])).entries()].sort((a, b) =>
    a[1].localeCompare(b[1]),
  );
  const years = [...new Set(filings.map((f) => f.fiscal_year))].sort();

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    onAsk(question.trim(), {
      tickers: ticker ? [ticker] : [],
      fiscal_years: year ? [Number(year)] : [],
      items: item ? [item] : [],
    });
  }

  return (
    <form className="question-form" onSubmit={submit}>
      <label htmlFor="question">Ask about the 10-K filings</label>
      <textarea
        id="question"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="e.g. What are AMD's main supply chain risks?"
        rows={3}
        maxLength={1000}
      />
      <div className="filters">
        <select aria-label="Company" value={ticker} onChange={(event) => setTicker(event.target.value)}>
          <option value="">Any company (auto-detect)</option>
          {companies.map(([symbol, company]) => (
            <option key={symbol} value={symbol}>
              {company}
            </option>
          ))}
        </select>
        <select aria-label="Fiscal year" value={year} onChange={(event) => setYear(event.target.value)}>
          <option value="">Any year</option>
          {years.map((value) => (
            <option key={value} value={value}>
              FY{value}
            </option>
          ))}
        </select>
        <select aria-label="Section" value={item} onChange={(event) => setItem(event.target.value)}>
          <option value="">Any section</option>
          {SECTIONS.map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
        <button type="submit" disabled={busy || !question.trim()}>
          {busy ? "Searching…" : "Ask"}
        </button>
      </div>
      <div className="examples">
        {EXAMPLES.map((example) => (
          <button key={example} type="button" className="example" onClick={() => setQuestion(example)}>
            {example}
          </button>
        ))}
      </div>
    </form>
  );
}
