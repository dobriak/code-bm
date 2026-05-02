/**
 * Tests for TrackTable formatting logic.
 */
import { describe, it, expect } from "vitest";

// Test the pure formatting function extracted from TrackTable
function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "";
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

describe("formatDuration", () => {
  it("formats 3 minutes 30 seconds", () => {
    expect(formatDuration(210000)).toBe("3:30");
  });

  it("formats 0 ms", () => {
    expect(formatDuration(0)).toBe("0:00");
  });

  it("formats seconds only", () => {
    expect(formatDuration(45000)).toBe("0:45");
  });

  it("handles null", () => {
    expect(formatDuration(null)).toBe("");
  });

  it("handles undefined", () => {
    expect(formatDuration(undefined)).toBe("");
  });

  it("formats long tracks", () => {
    expect(formatDuration(3600000)).toBe("60:00");
  });

  it("pads seconds with zero", () => {
    expect(formatDuration(61000)).toBe("1:01");
  });
});
