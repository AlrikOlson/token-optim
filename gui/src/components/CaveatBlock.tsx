/** Data-quality caveats (blueprint §5): a locked, register-free section.
 * Renders whatever caveats the data layer states; offers no dismissal. */
export function CaveatBlock({ caveats }: { caveats: readonly string[] }) {
  if (caveats.length === 0) return null;
  return (
    <aside
      className="caveat-block t-micro muted"
      aria-label="Data quality caveats"
    >
      <strong className="t-label ink">
        Data notes
      </strong>
      <ul>
        {caveats.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </aside>
  );
}
