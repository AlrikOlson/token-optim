import { afterEach, describe, expect, it, vi } from "vitest";
import { vtName, withTransition } from "./vt";

function setVT(fn: ((cb: () => void) => void) | undefined) {
  Object.defineProperty(document, "startViewTransition", {
    value: fn,
    configurable: true,
    writable: true,
  });
}

function setWebdriver(value: boolean) {
  Object.defineProperty(navigator, "webdriver", {
    value,
    configurable: true,
  });
}

afterEach(() => {
  Reflect.deleteProperty(document, "startViewTransition");
  setWebdriver(false);
  vi.unstubAllGlobals();
});

describe("withTransition — Act I plumbing", () => {
  it("runs the mutation plainly when the API is absent (jsdom path)", () => {
    const mutate = vi.fn();
    withTransition(mutate);
    expect(mutate).toHaveBeenCalledOnce();
  });

  it("routes through startViewTransition when available", () => {
    setWebdriver(false);
    const calls: string[] = [];
    setVT((cb) => {
      calls.push("vt");
      cb();
    });
    withTransition(() => calls.push("mutate"));
    expect(calls).toEqual(["vt", "mutate"]);
  });

  it("skips the API under prefers-reduced-motion", () => {
    const spy = vi.fn();
    setVT(spy);
    vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("reduce") }));
    const mutate = vi.fn();
    withTransition(mutate);
    expect(mutate).toHaveBeenCalledOnce();
    expect(spy).not.toHaveBeenCalled();
  });

  it("skips the API under automation (navigator.webdriver)", () => {
    const spy = vi.fn();
    setVT(spy);
    setWebdriver(true);
    const mutate = vi.fn();
    withTransition(mutate);
    expect(mutate).toHaveBeenCalledOnce();
    expect(spy).not.toHaveBeenCalled();
  });
});

describe("vtName — deterministic shared-element names", () => {
  it("same seed, same name; CSS-ident safe", () => {
    expect(vtName("case", "m.ruiz@contoso-demo.com")).toBe(
      vtName("case", "m.ruiz@contoso-demo.com"),
    );
    expect(vtName("case", "m.ruiz@contoso-demo.com")).toMatch(/^vt-case-[a-z0-9]+$/);
  });
  it("kinds and seeds separate namespaces", () => {
    expect(vtName("case", "x")).not.toBe(vtName("tile", "x"));
    expect(vtName("case", "x")).not.toBe(vtName("case", "y"));
  });
});
