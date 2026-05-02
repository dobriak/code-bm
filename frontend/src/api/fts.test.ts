/**
 * Tests for the FTS query builder logic (mirrored from backend).
 */
import { describe, it, expect } from "vitest";

// Import the FTS query logic (we'll replicate it here since it's backend-only)
function ftsQuery(text: string): string {
  const FTS_SPECIAL = /["*()\\:]/g;
  if (!text || !text.trim()) return '"*"';

  const tokens = text
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => {
      const escaped = word.replace(FTS_SPECIAL, "\\$&");
      return `${escaped}*`;
    });

  return tokens.join(" NEAR/4 ");
}

describe("FTS Query Builder", () => {
  it("returns match-all for empty string", () => {
    expect(ftsQuery("")).toBe('"*"');
  });

  it("returns match-all for whitespace", () => {
    expect(ftsQuery("   ")).toBe('"*"');
  });

  it("prefix-fuzzies a single word", () => {
    expect(ftsQuery("beatles")).toBe("beatles*");
  });

  it("joins multiple words with NEAR/4", () => {
    const result = ftsQuery("radiohead kid a");
    expect(result).toContain("radiohead*");
    expect(result).toContain("kid*");
    expect(result).toContain("a*");
    expect(result).toContain("NEAR/4");
  });

  it("escapes special characters", () => {
    const result = ftsQuery('test "quote"');
    expect(result).toContain('test*');
    expect(result).toContain('\\"quote\\"*');
  });
});
