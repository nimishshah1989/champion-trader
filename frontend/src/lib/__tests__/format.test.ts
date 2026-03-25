import { describe, it, expect } from "vitest";
import {
  formatINR,
  formatINRCompact,
  formatIndian,
  formatINRValue,
  formatLakhs,
  formatDateShort,
  todayISO,
  safeFixed,
  safeFormatINR,
} from "../format";

describe("formatINR (Intl.NumberFormat instance)", () => {
  it("formats a simple number with 2 decimal places and INR symbol", () => {
    const result = formatINR.format(1234.56);
    expect(result).toContain("1,234.56");
    // Should include the rupee symbol (₹ or INR depending on locale)
    expect(result).toMatch(/₹|INR/);
  });

  it("formats zero", () => {
    const result = formatINR.format(0);
    expect(result).toContain("0.00");
  });

  it("formats large numbers with Indian grouping (lakhs)", () => {
    const result = formatINR.format(250000);
    // Indian grouping: 2,50,000
    expect(result).toContain("2,50,000.00");
  });

  it("formats crore values correctly", () => {
    const result = formatINR.format(10000000);
    // Indian grouping: 1,00,00,000
    expect(result).toContain("1,00,00,000.00");
  });
});

describe("formatINRCompact", () => {
  it("formats without decimal places", () => {
    const result = formatINRCompact.format(1234.56);
    expect(result).toContain("1,235"); // rounded
    expect(result).not.toContain(".");
  });

  it("formats zero", () => {
    const result = formatINRCompact.format(0);
    expect(result).toContain("0");
  });
});

describe("formatIndian", () => {
  it("formats values >= 1 crore as Cr", () => {
    expect(formatIndian(10000000)).toBe("₹1.00 Cr");
    expect(formatIndian(25000000)).toBe("₹2.50 Cr");
    expect(formatIndian(150000000)).toBe("₹15.00 Cr");
  });

  it("formats values >= 1 lakh as L", () => {
    expect(formatIndian(100000)).toBe("₹1.00 L");
    expect(formatIndian(500000)).toBe("₹5.00 L");
    expect(formatIndian(250000)).toBe("₹2.50 L");
  });

  it("formats values below 1 lakh with Indian locale", () => {
    const result = formatIndian(50000);
    expect(result).toBe("₹50,000");
  });

  it("formats small values", () => {
    const result = formatIndian(100);
    expect(result).toBe("₹100");
  });
});

describe("formatINRValue", () => {
  it("delegates to formatINR.format", () => {
    expect(formatINRValue(1234.56)).toBe(formatINR.format(1234.56));
  });

  it("formats negative values", () => {
    const result = formatINRValue(-500);
    expect(result).toContain("500.00");
    expect(result).toMatch(/-/);
  });
});

describe("formatLakhs", () => {
  it("formats crore values with Cr suffix", () => {
    expect(formatLakhs(10000000)).toBe("1.00 Cr");
    expect(formatLakhs(25000000)).toBe("2.50 Cr");
  });

  it("formats lakh values with L suffix", () => {
    expect(formatLakhs(100000)).toBe("1.00L");
    expect(formatLakhs(500000)).toBe("5.00L");
  });

  it("formats sub-lakh values using formatINRCompact", () => {
    const result = formatLakhs(50000);
    expect(result).toBe(formatINRCompact.format(50000));
  });
});

describe("formatDateShort", () => {
  it("formats a date string to Indian short locale", () => {
    const result = formatDateShort("2025-03-15");
    // Should contain day, abbreviated month, 2-digit year
    expect(result).toMatch(/15/);
    expect(result).toMatch(/Mar/);
  });

  it("returns the original string for an invalid date", () => {
    const result = formatDateShort("not-a-date");
    // Invalid Date still returns a string from toLocaleDateString, or falls back
    // The function catches errors; check it doesn't throw
    expect(typeof result).toBe("string");
  });
});

describe("todayISO", () => {
  it("returns a YYYY-MM-DD string", () => {
    const result = todayISO();
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("matches today's date", () => {
    const expected = new Date().toISOString().split("T")[0];
    expect(todayISO()).toBe(expected);
  });
});

describe("safeFixed", () => {
  it("formats a number to fixed decimal places", () => {
    expect(safeFixed(3.14159, 2)).toBe("3.14");
    expect(safeFixed(100, 0)).toBe("100");
  });

  it("returns fallback for null", () => {
    expect(safeFixed(null, 2)).toBe("--");
  });

  it("returns fallback for undefined", () => {
    expect(safeFixed(undefined, 2)).toBe("--");
  });

  it("uses custom fallback", () => {
    expect(safeFixed(null, 2, "N/A")).toBe("N/A");
  });

  it("handles zero correctly (not treated as null)", () => {
    expect(safeFixed(0, 2)).toBe("0.00");
  });
});

describe("safeFormatINR", () => {
  it("formats a number as INR", () => {
    const result = safeFormatINR(1234.56);
    expect(result).toContain("1,234.56");
  });

  it("returns fallback for null", () => {
    expect(safeFormatINR(null)).toBe("--");
  });

  it("returns fallback for undefined", () => {
    expect(safeFormatINR(undefined)).toBe("--");
  });

  it("uses custom fallback", () => {
    expect(safeFormatINR(null, "N/A")).toBe("N/A");
  });

  it("handles zero correctly", () => {
    const result = safeFormatINR(0);
    expect(result).toContain("0.00");
  });
});
