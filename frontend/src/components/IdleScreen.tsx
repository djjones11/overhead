import { useEffect, useState } from "react";

export default function IdleScreen() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const date = now.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });

  return (
    <div className="relative h-full w-full flex flex-col items-center justify-center overflow-hidden animate-fade-in">
      {/* Faint world map backdrop for atmosphere */}
      <div
        className="absolute inset-0 opacity-[0.12] bg-center bg-cover"
        style={{
          backgroundImage:
            "url('https://upload.wikimedia.org/wikipedia/commons/8/83/Equirectangular_projection_SW.jpg')",
          filter: "invert(1) brightness(0.6)",
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black" />

      <div className="relative flex flex-col items-center gap-6">
        <span className="text-[7rem] leading-none font-semibold tracking-tight tabular-nums text-white">
          {time}
        </span>
        <span className="text-xl text-white/50 font-medium">{date}</span>

        <div className="mt-10 flex flex-col items-center gap-3">
          <div className="text-5xl opacity-30">✈</div>
          <p className="text-2xl text-white/70 font-medium">No aircraft currently overhead.</p>
          <p className="text-base text-white/30">Watching the skies nearby&hellip;</p>
        </div>
      </div>
    </div>
  );
}
