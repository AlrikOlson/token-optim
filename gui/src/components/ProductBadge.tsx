import type { Product } from "../domain";

const LABEL: Record<Product, { glyph: string; name: string }> = {
  m365: { glyph: "Ⓜ", name: "Microsoft 365 Copilot" },
  github: { glyph: "ⓖ", name: "GitHub Copilot" },
};

/** One canonical rendering of the product facet, everywhere it appears. */
export function ProductBadge({ product }: { product: Product }) {
  const { glyph, name } = LABEL[product];
  return (
    <span
      className="product-badge mono muted"
      role="img"
      aria-label={name}
      title={name}
    >
      {glyph}
    </span>
  );
}
