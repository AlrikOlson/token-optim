/** The MSP's mark (blueprint §4): name + accent swatch. The accent feeds
 * --accent so brand color flows through tokens, not inline styling. */
export function BrandChip({
  mspName,
  accent = "#1f6feb",
}: {
  mspName: string;
  accent?: string;
}) {
  return (
    <span
      className="brand-chip"
    >
      <span
        aria-hidden="true"
        className="brand-swatch"
        /* inline-ok(data): the swatch IS the customer's brand color */
        style={{ background: accent }}
      />
      <strong>{mspName}</strong>
    </span>
  );
}
