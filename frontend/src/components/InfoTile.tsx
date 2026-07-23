interface InfoTileProps {
  label: string;
  value: string;
  unit?: string;
  accent?: boolean;
}

export default function InfoTile({ label, value, unit, accent }: InfoTileProps) {
  return (
    <div className="bg-surface-card/80 backdrop-blur-xl rounded-2xl px-5 py-4 flex flex-col gap-1 border border-surface-border/60">
      <span className="text-[11px] uppercase tracking-wider text-white/40 font-medium">{label}</span>
      <span className={`text-2xl font-semibold tabular-nums ${accent ? "text-accent-blue" : "text-white"}`}>
        {value}
        {unit && <span className="text-sm font-medium text-white/40 ml-1">{unit}</span>}
      </span>
    </div>
  );
}
