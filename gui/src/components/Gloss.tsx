import type { ReactNode } from "react";
import { GLOSSARY, type GlossKey } from "../clarity";

/** A Memo-register term with its plain meaning one hover/tap/focus away.
 * Semantic <abbr> so the gloss is native (title) and keyboard-reachable
 * (tabIndex) — progressive disclosure, not a tooltip library. The term
 * keeps the Memo voice; the gloss is plain register from the GLOSSARY. */
export function Gloss({ term, children }: { term: GlossKey; children: ReactNode }) {
  return (
    <abbr className="gloss" title={GLOSSARY[term]} tabIndex={0}>
      {children}
    </abbr>
  );
}
