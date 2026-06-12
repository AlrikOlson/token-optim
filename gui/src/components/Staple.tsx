/** A staple (gui-6): the hardware that pins an attachment to a case file.
 * Decorative — pure SVG, metallic gradient, tiny cast shadow. */
export function Staple() {
  return (
    <svg
      className="staple"
      width="34"
      height="12"
      viewBox="0 0 34 12"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="staple-metal" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#c8c4ba" />
          <stop offset="0.5" stopColor="#8e8a80" />
          <stop offset="1" stopColor="#5e5a52" />
        </linearGradient>
      </defs>
      <path
        d="M3 11 L3 3 L31 3 L31 11"
        fill="none"
        stroke="url(#staple-metal)"
        strokeWidth="2.6"
        strokeLinecap="square"
      />
      <path
        d="M3 11 L3 4 L31 4 L31 11"
        fill="none"
        stroke="rgba(20,24,18,0.35)"
        strokeWidth="1"
        transform="translate(0.6 1)"
      />
    </svg>
  );
}
