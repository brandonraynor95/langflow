import { formatDate, formatTimestamp, statusBgColors, statusColors } from "../helpers";

describe("Memories helpers", () => {
  it("returns fallback values for empty dates", () => {
    expect(formatDate()).toBe("Never");
    expect(formatTimestamp()).toBe("-");
  });

  it("returns original value for invalid date strings", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date");
    expect(formatTimestamp("also-not-a-date")).toBe("also-not-a-date");
  });

  it("formats valid dates", () => {
    const date = formatDate("2025-01-01T10:30:00.000Z");
    const timestamp = formatTimestamp("2025-01-01 10:30:00");

    expect(date).toContain("Jan");
    expect(timestamp).toContain("Jan");
  });

  it("exposes expected status color mappings", () => {
    expect(statusColors.failed).toBe("text-destructive");
    expect(statusBgColors.generating).toBe("bg-primary/10");
  });
});
