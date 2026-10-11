import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Answer } from "../api";
import { AnswerView } from "./AnswerView";

const source = {
  passage_id: "AMD-10K-2022#0001",
  filing_id: "AMD-10K-2022",
  label: "Advanced Micro Devices, Inc. · 10-K FY2022 · Item 1A Risk Factors · p. 17",
  company: "Advanced Micro Devices, Inc.",
  ticker: "AMD",
  fiscal_year: 2022,
  item: "1A",
  item_heading: "Risk Factors",
  pages: { start: 17, end: 17 },
  document_url: "/api/v1/filings/AMD-10K-2022/document#page=17",
};

function answer(overrides: Partial<Answer> = {}): Answer {
  return {
    question: "Who makes AMD's chips?",
    status: "grounded",
    segments: [
      { text: "AMD relies on TSMC for wafers.", citation_ids: ["c1"] },
      { text: " It also <b>plans</b> new fabs.", citation_ids: [] },
    ],
    citations: [{ ...source, id: "c1", quote: "We rely on TSMC to manufacture our wafers." }],
    evidence: [],
    scope: { tickers: ["AMD"], fiscal_years: [2022], items: [], source: "detected" },
    meta: { generator: "claude", model: "claude-opus-5-5", notice: null, coverage: 0.7, timings_ms: {} },
    ...overrides,
  };
}

describe("AnswerView", () => {
  it("numbers citation chips and reports which source was chosen", async () => {
    const onSelect = vi.fn();
    render(<AnswerView answer={answer()} onSelectCitation={onSelect} />);

    await userEvent.click(screen.getByRole("button", { name: "Citation 1" }));

    expect(onSelect).toHaveBeenCalledWith("AMD-10K-2022#0001");
    expect(screen.getByText("Grounded in the filings")).toBeInTheDocument();
  });

  it("renders model output as plain text, never as HTML", () => {
    render(<AnswerView answer={answer()} onSelectCitation={() => {}} />);

    expect(screen.getByText(/It also <b>plans<\/b> new fabs\./)).toBeInTheDocument();
  });

  it("marks uncited claims when the answer is only partly supported", () => {
    render(<AnswerView answer={answer({ status: "partially_grounded" })} onSelectCitation={() => {}} />);

    expect(screen.getByTitle("Not supported by a citation")).toHaveTextContent("It also <b>plans</b> new fabs.");
  });

  it("explains the scope that was searched and any notice", () => {
    const notice = "Showing the most relevant passages: no LLM is configured (set ANTHROPIC_API_KEY).";
    render(
      <AnswerView
        answer={answer({ status: "extractive_fallback", meta: { ...answer().meta, notice } })}
        onSelectCitation={() => {}}
      />,
    );

    expect(screen.getByText(/AMD · FY2022 \(detected from your question\)/)).toBeInTheDocument();
    expect(screen.getByText(notice)).toBeInTheDocument();
    expect(screen.getByText("Relevant passages (no AI summary)")).toBeInTheDocument();
  });
});
