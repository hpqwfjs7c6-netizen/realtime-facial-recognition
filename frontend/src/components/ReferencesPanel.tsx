"use client";

import React, { useRef, useState } from "react";
import { Trash2, UploadCloud, UserPlus } from "lucide-react";
import type { ReferenceFace } from "@/lib/types";

interface Props {
  references: ReferenceFace[];
  onAdd: (name: string, file: File) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

export default function ReferencesPanel({
  references,
  onAdd,
  onDelete,
}: Props) {
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const canSubmit = name.trim().length > 0 && file !== null && !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !name.trim()) return;
    setSubmitting(true);
    try {
      await onAdd(name.trim(), file);
      setName("");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-5 overflow-y-auto pr-2 custom-scrollbar">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <label
            htmlFor="ref-name"
            className="text-xs font-medium text-slate-400"
          >
            Nom de la personne
          </label>
          <input
            id="ref-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ex. Alice Martin"
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label
            htmlFor="ref-file"
            className="text-xs font-medium text-slate-400"
          >
            Photo de référence
          </label>
          <input
            id="ref-file"
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-xs text-slate-400 file:mr-3 file:cursor-pointer file:rounded-lg file:border-0 file:bg-indigo-600 file:px-3 file:py-2 file:text-xs file:font-medium file:text-white hover:file:bg-indigo-500"
          />
        </div>

        <button
          type="submit"
          disabled={!canSubmit}
          className="flex items-center justify-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white transition-colors duration-200 hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-amber-400"
        >
          {submitting ? (
            <UploadCloud className="h-4 w-4 animate-pulse" aria-hidden="true" />
          ) : (
            <UserPlus className="h-4 w-4" aria-hidden="true" />
          )}
          {submitting ? "Enrôlement…" : "Enrôler le visage"}
        </button>
      </form>

      <div className="border-t border-slate-700/50 pt-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Visages enrôlés ({references.length})
        </p>
        {references.length === 0 ? (
          <p className="text-xs text-slate-500">
            Aucune référence. Ajoutez un visage pour activer la reconnaissance.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {references.map((ref) => (
              <li
                key={ref.id}
                className="flex items-center justify-between rounded-lg border border-slate-700/50 bg-slate-800/40 px-3 py-2 text-sm"
              >
                <span className="text-slate-200">{ref.name}</span>
                <button
                  onClick={() => onDelete(ref.id)}
                  aria-label={`Supprimer ${ref.name}`}
                  className="rounded p-1.5 text-slate-500 transition-colors hover:bg-rose-500/10 hover:text-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
