"use client";

import { RefreshCw } from "lucide-react";
import type { FaceData } from "@/lib/types";

function Angle({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col rounded bg-slate-900 p-2">
      <span className="text-slate-500">{label}</span>
      <span className="font-mono text-slate-300">{value.toFixed(1)}°</span>
    </div>
  );
}

export default function TelemetryPanel({ faces }: { faces: FaceData[] }) {
  if (faces.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-sm text-slate-500">
        <RefreshCw
          className="h-8 w-8 animate-spin-slow opacity-50"
          aria-hidden="true"
        />
        <p>En attente d&apos;un visage…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 overflow-y-auto pr-2 custom-scrollbar">
      {faces.map((face, index) => {
        const lookingDirect =
          face.pitch >= -15 &&
          face.pitch <= 15 &&
          face.yaw >= -15 &&
          face.yaw <= 15;
        return (
          <div
            key={`tel-${index}`}
            className="flex flex-col gap-4 rounded-xl border border-slate-700/50 bg-slate-800/50 p-4"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-200">
                {face.name || `Visage #${index + 1}`}
              </span>
              <span
                className={`rounded px-2 py-1 text-xs font-medium ${
                  face.recognized
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-rose-500/20 text-rose-400"
                }`}
              >
                {face.recognized ? "✓ Authentifié" : "✗ Non reconnu"}
              </span>
            </div>

            <div className="flex flex-col gap-2 text-xs text-slate-400">
              <div className="flex justify-between">
                <span>Action système</span>
                <span className="font-mono text-amber-400">
                  {face.system_action}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Confiance</span>
                <span className="font-mono text-slate-200">
                  {(face.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span>Regard direct</span>
                <span
                  className={`font-bold ${
                    lookingDirect ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  {lookingDirect ? "Oui" : "Non (regarde ailleurs)"}
                </span>
              </div>
            </div>

            <div className="border-t border-slate-700/50 pt-2">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Angles de tête (Azure)
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <Angle label="Pitch (haut/bas)" value={face.pitch} />
                <Angle label="Yaw (gauche/droite)" value={face.yaw} />
                <div className="col-span-2">
                  <Angle label="Roll (inclinaison)" value={face.roll} />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
