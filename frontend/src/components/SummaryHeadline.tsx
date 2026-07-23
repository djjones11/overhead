interface SummaryHeadlineProps {
  summary: string;
  isMilitary: boolean;
  isHelicopter: boolean;
}

export default function SummaryHeadline({ summary, isMilitary, isHelicopter }: SummaryHeadlineProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        {isMilitary && (
          <span className="text-xs font-semibold uppercase tracking-wide bg-accent-red/20 text-accent-red px-2.5 py-1 rounded-full">
            Military
          </span>
        )}
        {isHelicopter && (
          <span className="text-xs font-semibold uppercase tracking-wide bg-accent-orange/20 text-accent-orange px-2.5 py-1 rounded-full">
            Helicopter
          </span>
        )}
      </div>
      <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-white leading-tight max-w-4xl">
        {summary}
      </h1>
    </div>
  );
}
