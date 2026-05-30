"use client";

import React, { useEffect, useRef, useState } from "react";
import { Check, Pencil, Sparkles, Trash2, UploadCloud, UserPlus, X } from "lucide-react";
import { api } from "@/lib/api";
import type { ReferenceFace } from "@/lib/types";

interface Props {
  references: ReferenceFace[];
  onAdd: (name: string, file: File) => Promise<void>;
  onRename: (id: number, name: string) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

function ReferenceRow({
  reference,
  onRename,
  onDelete,
}: {
  reference: ReferenceFace;
  onRename: (id: number, name: string) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(reference.name);
  const [thumb, setThumb] = useState<string | null>(null);

  // Charge la miniature du visage (object URL révoqué au démontage).
  useEffect(() => {
    let url: string | null = null;
    let active = true;
    void api.referenceImageUrl(reference.id).then((u) => {
      if (active && u) {
        url = u;
        setThumb(u);
      }
    });
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [reference.id]);

  const save = async () => {
    const name = draft.trim();
    if (name && name !== reference.name) await onRename(reference.id, name);
    setEditing(false);
  };

  return (
    <li className="flex items-center gap-3 rounded-lg border border-slate-700/50 bg-slate-800/40 px-3 py-2 text-sm">
      {thumb ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={thumb}
          alt={reference.name}
          className="h-10 w-10 shrink-0 rounded-md object-cover"
        />
      ) : (
        <div className="h-10 w-10 shrink-0 rounded-md bg-slate-700/50" />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {editing ? (
          <div className="flex items-center gap-1">
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void save();
                if (e.key === "Escape") setEditing(false);
              }}
              className="w-full rounded border border-slate-600 bg-slate-900 px-2 py-1 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
            />
            <button
              onClick={() => void save()}
              aria-label="Valider le nom"
              className="rounded p-1 text-emerald-400 hover:bg-emerald-500/10"
            >
              <Check className="h-4 w-4" />
            </button>
            <button
              onClick={() => setEditing(false)}
              aria-label="Annuler"
              className="rounded p-1 text-slate-400 hover:bg-slate-600/30"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="truncate text-slate-200">{reference.name}</span>
            {reference.auto && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-300">
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                auto
              </span>
            )}
          </div>
        )}
      </div>

      {!editing && (
        <>
          <button
            onClick={() => {
              setDraft(reference.name);
              setEditing(true);
            }}
            aria-label={`Renommer ${reference.name}`}
            className="rounded p-1.5 text-slate-500 transition-colors hover:bg-indigo-500/10 hover:text-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            onClick={() => void onDelete(reference.id)}
            aria-label={`Supprimer ${reference.name}`}
            className="rounded p-1.5 text-slate-500 transition-colors hover:bg-rose-500/10 hover:text-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-400"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </>
      )}
    </li>
  );
}

export default function ReferencesPanel({
  references,
  onAdd,
  onRename,
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
        <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Visages enrôlés ({references.length})
        </p>
        <p className="mb-3 flex items-center gap-1 text-[11px] text-slate-500">
          <Sparkles className="h-3 w-3 text-amber-400" aria-hidden="true" />
          Les visages détectés de face sont enrôlés automatiquement. Renommez-les
          pour les identifier.
        </p>
        {references.length === 0 ? (
          <p className="text-xs text-slate-500">
            Aucune référence pour l&apos;instant. Regardez la caméra de face pour
            un enrôlement automatique.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {references.map((reference) => (
              <ReferenceRow
                key={reference.id}
                reference={reference}
                onRename={onRename}
                onDelete={onDelete}
              />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
