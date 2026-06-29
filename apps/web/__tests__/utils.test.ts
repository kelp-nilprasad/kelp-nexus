import { describe, expect, it } from "vitest";
import { cn, initials, relativeTime } from "@/lib/utils";

describe("cn", () => {
  it("merges and dedupes tailwind classes", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
    expect(cn("text-sm", false && "hidden", "font-bold")).toBe("text-sm font-bold");
  });
});

describe("initials", () => {
  it("returns up to two uppercase initials", () => {
    expect(initials("Ada Lovelace")).toBe("AL");
    expect(initials("priya")).toBe("P");
  });
});

describe("relativeTime", () => {
  it("formats recent times", () => {
    const now = new Date().toISOString();
    expect(relativeTime(now)).toBe("just now");
  });
});
