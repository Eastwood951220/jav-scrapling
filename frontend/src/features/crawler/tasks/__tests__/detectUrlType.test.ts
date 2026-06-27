import { describe, it, expect } from "vitest";
import { detectUrlType } from "../TaskForm";

describe("detectUrlType", () => {
  it("should detect tags type from /tags path without trailing slash", () => {
    const url = "https://javdb.com/tags?c7=212&c10=1";
    expect(detectUrlType(url)).toBe("tags");
  });

  it("should detect tags type from /tags/ path with trailing slash", () => {
    const url = "https://javdb.com/tags/";
    expect(detectUrlType(url)).toBe("tags");
  });

  it("should detect tags type from /tags/123 path", () => {
    const url = "https://javdb.com/tags/123";
    expect(detectUrlType(url)).toBe("tags");
  });

  it("should detect actors type", () => {
    expect(detectUrlType("https://javdb.com/actors/abc")).toBe("actors");
  });

  it("should detect search type", () => {
    expect(detectUrlType("https://javdb.com/search?q=test")).toBe("search");
  });

  it("should return null for unknown paths", () => {
    expect(detectUrlType("https://javdb.com/unknown")).toBeNull();
  });

  it("should return null for invalid URLs", () => {
    expect(detectUrlType("not-a-url")).toBeNull();
  });
});
