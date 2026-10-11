import type { Answer, Scope, Status } from "../api";

const STATUS_LABELS: Record<Status, string> = {
  grounded: "Grounded in the filings",
  partially_grounded: "Partly supported: check the unmarked sentences",
  insufficient_evidence: "Not found in the filings",
  extractive_fallback: "Relevant passages (no AI summary)",
};

function describeScope(scope: Scope): string {
  const parts = [...scope.tickers, ...scope.fiscal_years.map((year) => `FY${year}`)];
  if (scope.items.length) parts.push(`Item ${scope.items.join(", ")}`);
  if (!parts.length) return "All indexed filings";
  const origin = scope.source === "detected" ? " (detected from your question)" : " (your filters)";
  return parts.join(" · ") + origin;
}

interface Props {
  answer: Answer;
  onSelectCitation: (passageId: string) => void;
}

export function AnswerView({ answer, onSelectCitation }: Props) {
  const numbers = new Map(answer.citations.map((citation, index) => [citation.id, index + 1]));
  const passageOf = new Map(answer.citations.map((citation) => [citation.id, citation.passage_id]));
  const flagUncited = answer.status === "partially_grounded";

  return (
    <section className="answer" aria-live="polite">
      <div className="answer-header">
        <span className={`status status-${answer.status}`}>{STATUS_LABELS[answer.status]}</span>
        <span className="scope">Searched: {describeScope(answer.scope)}</span>
      </div>
      {answer.meta.notice && <p className="notice">{answer.meta.notice}</p>}
      <p className="answer-text">
        {answer.segments.map((segment, index) => (
          <span key={index}>
            {flagUncited && segment.citation_ids.length === 0 && segment.text.trim().split(/\s+/).length >= 5 ? (
              <span className="uncited" title="Not supported by a citation">
                {segment.text}
              </span>
            ) : (
              segment.text
            )}
            {segment.citation_ids.map((id) => (
              <button
                key={id}
                type="button"
                className="chip"
                aria-label={`Citation ${numbers.get(id)}`}
                onClick={() => onSelectCitation(passageOf.get(id) ?? "")}
              >
                {numbers.get(id)}
              </button>
            ))}
          </span>
        ))}
      </p>
      {answer.meta.model && <p className="meta">Answered by {answer.meta.model}</p>}
    </section>
  );
}
