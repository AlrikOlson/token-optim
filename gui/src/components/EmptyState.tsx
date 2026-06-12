import type { ReactNode } from "react";

/** A plain-register empty state (gui-14): says what would appear here and
 * what actually makes it appear. Guidance must be TRUE of the running app —
 * never a button for a flow that doesn't exist. */
export function EmptyState({
  what,
  how,
  children,
}: {
  /** what belongs in this space */
  what: string;
  /** the real action that fills it */
  how: string;
  /** optional REAL affordance (an existing, working control) */
  children?: ReactNode;
}) {
  return (
    <div className="empty-state" role="status">
      <p className="t-label m-0">{what}</p>
      <p className="muted m-0">{how}</p>
      {children}
    </div>
  );
}
