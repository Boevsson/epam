import type { Answer, Evidence } from "../api";

interface Props {
  answer: Answer;
  selected: string | null;
  showRetrieval: boolean;
}

export function SourceList({ answer, selected, showRetrieval }: Props) {
  if (!answer.evidence.length) return null;
  const quotes = new Map<string, string[]>();
  for (const citation of answer.citations) {
    quotes.set(citation.passage_id, [...(quotes.get(citation.passage_id) ?? []), citation.quote]);
  }
  const numbers = new Map<string, number[]>();
  answer.citations.forEach((citation, index) => {
    numbers.set(citation.passage_id, [...(numbers.get(citation.passage_id) ?? []), index + 1]);
  });

  return (
    <section className="sources">
      <h2>Sources</h2>
      {answer.evidence.map((evidence) => (
        <SourceCard
          key={evidence.passage_id}
          evidence={evidence}
          quotes={quotes.get(evidence.passage_id) ?? []}
          citationNumbers={numbers.get(evidence.passage_id) ?? []}
          selected={selected === evidence.passage_id}
          showRetrieval={showRetrieval}
        />
      ))}
    </section>
  );
}

interface CardProps {
  evidence: Evidence;
  quotes: string[];
  citationNumbers: number[];
  selected: boolean;
  showRetrieval: boolean;
}

function SourceCard({ evidence, quotes, citationNumbers, selected, showRetrieval }: CardProps) {
  const pages = evidence.pages.start === evidence.pages.end
    ? `p. ${evidence.pages.start}`
    : `pp. ${evidence.pages.start}-${evidence.pages.end}`;
  const ranks = Object.entries(evidence.retrieval.ranks);

  return (
    <article id={`source-${evidence.passage_id}`} className={`source${selected ? " selected" : ""}`}>
      <header>
        {citationNumbers.length > 0 && <span className="cited-as">[{citationNumbers.join(", ")}]</span>}
        <strong>{evidence.company}</strong> · 10-K FY{evidence.fiscal_year} · Item {evidence.item}{" "}
        {evidence.item_heading} · {pages}
        <a href={evidence.document_url} target="_blank" rel="noreferrer">
          Open page ↗
        </a>
      </header>
      <p>
        {evidence.sentences.map((sentence, index) => (
          <span key={index} className={quotes.some((quote) => quote.includes(sentence)) ? "cited" : undefined}>
            {sentence}{" "}
          </span>
        ))}
      </p>
      {showRetrieval && (
        <footer className="retrieval">
          {ranks.map(([name, rank]) => `${name} #${rank.rank} (${rank.score.toFixed(3)})`).join(" · ")}
          {ranks.length > 1 && ` · fused ${evidence.retrieval.fused_score.toFixed(4)}`}
        </footer>
      )}
    </article>
  );
}
