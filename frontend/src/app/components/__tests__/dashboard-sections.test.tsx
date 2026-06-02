import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DrawdownBanner } from "../dashboard-sections";
import type { RiskStatus } from "@/lib/intelligence-api";

function risk(dd: Partial<RiskStatus["drawdown"]>, frozen = false): RiskStatus {
  return {
    open_positions: 0, total_risk_pct: 0, max_risk_pct: 10, frozen, frozen_reason: null,
    positions: [],
    drawdown: {
      halted: false, equity: 1000000, peak: 1000000, drawdown_pct: 0,
      halt_threshold_pct: 15, resume_threshold_pct: 7.5, ...dd,
    },
  };
}

describe("DrawdownBanner", () => {
  it("renders nothing when there is no risk data", () => {
    const { container } = render(<DrawdownBanner risk={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing before any equity curve exists (peak <= 0)", () => {
    const { container } = render(<DrawdownBanner risk={risk({ peak: 0 })} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows a loud HALTED banner once the 15% breaker trips", () => {
    render(<DrawdownBanner risk={risk({ halted: true, equity: 990000, peak: 1080000, drawdown_pct: 8.33 })} />);
    expect(screen.getByText(/New entries HALTED/i)).toBeInTheDocument();
    expect(screen.getByText(/breaker at 15%/i)).toBeInTheDocument();
    expect(screen.getByText(/resumes new entries/i)).toBeInTheDocument();
  });

  it("treats a frozen flag as halted even if drawdown.halted is false", () => {
    render(<DrawdownBanner risk={risk({ halted: false, equity: 990000, peak: 1080000, drawdown_pct: 8.33 }, true)} />);
    expect(screen.getByText(/New entries HALTED/i)).toBeInTheDocument();
  });

  it("shows the subtle gauge when in drawdown but not halted", () => {
    render(<DrawdownBanner risk={risk({ halted: false, equity: 1020000, peak: 1080000, drawdown_pct: 5.6 })} />);
    expect(screen.getByText(/Drawdown breaker/i)).toBeInTheDocument();
    expect(screen.getByText(/to halt/i)).toBeInTheDocument();
    expect(screen.queryByText(/New entries HALTED/i)).not.toBeInTheDocument();
  });
});
