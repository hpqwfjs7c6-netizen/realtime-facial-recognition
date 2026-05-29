"use client";

import { Pause, Play } from "lucide-react";

interface Props {
  intervalMs: number;
  onIntervalChange: (ms: number) => void;
  running: boolean;
  onToggleRunning: () => void;
}

export default function SettingsPanel({
  intervalMs,
  onIntervalChange,
  running,
  onToggleRunning,
}: Props) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <button
          onClick={onToggleRunning}
          className={`flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white transition-colors duration-200 focus:outline-none focus:ring-2 ${
            running
              ? "bg-rose-600 hover:bg-rose-500 focus:ring-rose-400"
              : "bg-emerald-600 hover:bg-emerald-500 focus:ring-emerald-400"
          }`}
        >
          {running ? (
            <>
              <Pause className="h-4 w-4" aria-hidden="true" /> Mettre en pause
            </>
          ) : (
            <>
              <Play className="h-4 w-4" aria-hidden="true" /> Reprendre l&apos;analyse
            </>
          )}
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <label
          htmlFor="interval"
          className="flex justify-between text-xs font-medium text-slate-400"
        >
          <span>Intervalle de capture</span>
          <span className="font-mono text-slate-200">
            {(intervalMs / 1000).toFixed(1)} s
          </span>
        </label>
        <input
          id="interval"
          type="range"
          min={1000}
          max={10000}
          step={500}
          value={intervalMs}
          onChange={(e) => onIntervalChange(Number(e.target.value))}
          className="w-full accent-amber-500"
        />
        <p className="text-xs text-slate-500">
          Fréquence d&apos;envoi des images au backend. Plus l&apos;intervalle
          est court, plus l&apos;analyse est réactive (mais coûteuse).
        </p>
      </div>
    </div>
  );
}
