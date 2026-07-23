import { useAircraftData } from "./hooks/useAircraftData";
import AircraftDisplay from "./components/AircraftDisplay";
import IdleScreen from "./components/IdleScreen";

export default function App() {
  const { data, connected } = useAircraftData();

  const hasAircraft = Boolean(data?.aircraft);

  return (
    <div className="h-screen w-screen bg-black text-white font-sans overflow-hidden relative">
      {hasAircraft && data?.aircraft ? (
        <AircraftDisplay aircraft={data.aircraft} home={data.home} />
      ) : (
        <IdleScreen />
      )}

      {/* Unobtrusive status indicator, bottom-right */}
      <div className="absolute bottom-4 right-5 flex items-center gap-2 text-xs text-white/25">
        {data?.message && <span className="text-accent-orange/70">{data.message}</span>}
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            connected ? "bg-accent-green/70" : "bg-white/20 animate-pulse-slow"
          }`}
        />
        <span>{data?.provider ?? "connecting"}</span>
      </div>
    </div>
  );
}
