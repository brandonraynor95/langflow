/**
 * Tests for assistant panel message helpers.
 *
 * Tests randomized message functions used for reasoning/validation UI states.
 */

import {
  getRandomPlaceholderMessage,
  getRandomThinkingMessage,
} from "../messages";

describe("getRandomThinkingMessage", () => {
  it("should return a non-empty string ending with '...'", () => {
    const result = getRandomThinkingMessage();

    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toMatch(/\.\.\.$/);
  });
});

describe("getRandomPlaceholderMessage", () => {
  it("should return from same pool as thinking message", () => {
    const spy = jest.spyOn(Math, "random").mockReturnValue(0);
    const thinking = getRandomThinkingMessage();
    const placeholder = getRandomPlaceholderMessage();
    spy.mockRestore();

    expect(thinking).toBe(placeholder);
  });
});

describe("deterministic Math.random", () => {
  it("should return first element when Math.random is 0", () => {
    const spy = jest.spyOn(Math, "random").mockReturnValue(0);
    const result = getRandomThinkingMessage();
    spy.mockRestore();

    // Math.floor(0 * 8) = 0 → first element "Thinking..."
    expect(result).toBe("Thinking...");
  });

  it("should return last element when Math.random is 0.999", () => {
    const spy = jest.spyOn(Math, "random").mockReturnValue(0.999);
    const result = getRandomThinkingMessage();
    spy.mockRestore();

    // Math.floor(0.999 * 8) = Math.floor(7.992) = 7 → last element "Almost there..."
    expect(result).toBe("Almost there...");
  });
});
