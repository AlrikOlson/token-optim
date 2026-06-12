/** The savings meter (blueprint §4): renders projected_savings() output and
 * nothing else — values never lie. Styled entirely by the system classes. */
export function SavingsMeter({
  monthlyUsd,
  label = "Savings found",
}: {
  monthlyUsd: number;
  label?: string;
}) {
  const exact = `$${monthlyUsd.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  return (
    <div
      className="savings-meter savings t-poster ta-right"
      role="status"
      aria-label={`${label}: ${exact} per month`}
    >
      <span className="t-label muted block">
        {label}
      </span>
      <strong className="t-figure press" data-testid="savings-value">
        {exact}
      </strong>
      <span className="t-micro muted">/mo</span>
    </div>
  );
}
