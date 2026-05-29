"use client";

import { History } from "lucide-react";
import type { RecognitionEvent } from "@/lib/types";

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Math.max(0, Date.now() - then) / 1000;
  if (diff < 60) return `il y a ${Math.floor(diff)} s`;
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)} h`;
  return new Date(iso).toLocaleDateString("fr-FR");
}

export default function HistoryPanel({
  events,
}: {
  events: RecognitionEvent[];
}) {
  if (events.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-sm text-slate-500">
        <History className="h-8 w-8 opacity-50" aria-hidden="true" />
        <p>Aucun événement pour le moment.</p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-2 overflow-y-auto pr-2 custom-scrollbar">
      {events.map((e) => (
        <li
          key={e.id}
          className="flex items-center justify-between rounded-lg border border-slate-700/50 bg-slate-800/40 px-3 py-2 text-xs"
        >
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${
                e.recognized ? "bg-emerald-400" : "bg-rose-500"
              }`}
              aria-hidden="true"
            />
            <span className="font-medium text-slate-200">
              {e.recognized ? e.name || "Reconnu" : "Inconnu"}
            </span>
            <span className="font-mono text-slate-500">
              {(e.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <time className="font-mono text-slate-500" dateTime={e.created_at}>
            {timeAgo(e.created_at)}
          </time>
        </li>
      ))}
    </ul>
  );
}
