/** Act I — View Transitions plumbing (Baseline since 2025-10).
 *
 * withTransition wraps a state mutation in document.startViewTransition so
 * shared-element morphs (the card flight, tile→case-file) run on the
 * platform primitive. Fallbacks: no API (jsdom, old browsers) or
 * prefers-reduced-motion → the mutation runs plainly and instantly. */

import { flushSync } from "react-dom";
import { stableHash } from "./hash";

function reducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** Automated runs (Playwright/story tests set navigator.webdriver) skip the
 * transition so DOM updates stay synchronous and assertions deterministic;
 * the motion itself is verified by eye in /gui-scrutiny. */
function automated(): boolean {
  return typeof navigator !== "undefined" && navigator.webdriver === true;
}

export function withTransition(mutate: () => void): void {
  if (
    typeof document.startViewTransition === "function" &&
    !reducedMotion() &&
    !automated()
  ) {
    document.startViewTransition(() => {
      flushSync(mutate);
    });
  } else {
    mutate();
  }
}

/** Deterministic view-transition-name (CSS ident-safe) — same determinism
 * law as stamp tilts: the same object always wears the same name. */
export function vtName(kind: string, seed: string): string {
  return `vt-${kind}-${stableHash(seed).toString(36)}`;
}
