"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Webcam from "react-webcam";
import { Activity, Cpu, History, Settings, Users, Zap } from "lucide-react";

import { api } from "@/lib/api";
import type { FaceData, RecognitionEvent, ReferenceFace } from "@/lib/types";
import { ToastProvider, useToast } from "@/components/Toast";
import CameraView from "@/components/CameraView";
import TelemetryPanel from "@/components/TelemetryPanel";
import HistoryPanel from "@/components/HistoryPanel";
import ReferencesPanel from "@/components/ReferencesPanel";
import SettingsPanel from "@/components/SettingsPanel";

type Tab = "telemetry" | "history" | "references" | "settings";

const TABS: { id: Tab; label: string; icon: typeof Cpu }[] = [
  { id: "telemetry", label: "Télémétrie", icon: Cpu },
  { id: "history", label: "Historique", icon: History },
  { id: "references", label: "Références", icon: Users },
  { id: "settings", label: "Réglages", icon: Settings },
];

function Dashboard() {
  const { notify } = useToast();
  const webcamRef = useRef<Webcam>(null);
  const inFlightRef = useRef(false);
  const cameraSizeRef = useRef({ width: 0, height: 0 });

  const [faces, setFaces] = useState<FaceData[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [cameraSize, setCameraSize] = useState({ width: 0, height: 0 });
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  const [tab, setTab] = useState<Tab>("telemetry");
  const [references, setReferences] = useState<ReferenceFace[]>([]);
  const [events, setEvents] = useState<RecognitionEvent[]>([]);

  const [running, setRunning] = useState(true);
  const [intervalMs, setIntervalMs] = useState(3000);

  // --- Santé du backend ---
  const checkHealth = useCallback(async () => {
    try {
      const h = await api.health();
      setBackendOnline(true);
      if (!h.azure_configured) {
        notify("Azure Face API non configuré côté backend.", "error");
      }
    } catch {
      setBackendOnline(false);
    }
  }, [notify]);

  // --- Références ---
  const loadReferences = useCallback(async () => {
    try {
      const { references } = await api.listReferences();
      setReferences(references);
    } catch (err) {
      notify(`Chargement des références : ${(err as Error).message}`, "error");
    }
  }, [notify]);

  const addReference = useCallback(
    async (name: string, file: File) => {
      try {
        await api.addReference(name, file);
        notify(`« ${name} » enrôlé avec succès.`, "success");
        await loadReferences();
      } catch (err) {
        notify(`Échec de l'enrôlement : ${(err as Error).message}`, "error");
      }
    },
    [notify, loadReferences],
  );

  const renameReference = useCallback(
    async (id: number, name: string) => {
      try {
        await api.updateReference(id, name);
        notify(`Référence renommée « ${name} ».`, "success");
        await loadReferences();
      } catch (err) {
        notify(`Échec du renommage : ${(err as Error).message}`, "error");
      }
    },
    [notify, loadReferences],
  );

  const deleteReference = useCallback(
    async (id: number) => {
      try {
        await api.deleteReference(id);
        notify("Référence supprimée.", "success");
        await loadReferences();
      } catch (err) {
        notify(`Échec de la suppression : ${(err as Error).message}`, "error");
      }
    },
    [notify, loadReferences],
  );

  // --- Historique ---
  const loadHistory = useCallback(async () => {
    try {
      const { events } = await api.history(30);
      setEvents(events);
    } catch {
      /* silencieux : non bloquant */
    }
  }, []);

  // --- Boucle de capture (anti-empilement) ---
  const captureAndAnalyze = useCallback(async () => {
    if (!webcamRef.current || inFlightRef.current) return;
    const imageSrc = webcamRef.current.getScreenshot();
    if (!imageSrc) return;

    inFlightRef.current = true;
    setIsAnalyzing(true);
    try {
      const data = await api.analyzeFace(imageSrc);
      // Filtre anti-faux-positifs : ignore les visages trop petits par rapport
      // au cadre (arrière-plan, TV, reflets). Seuil : 6 % de la largeur.
      const w = cameraSizeRef.current.width;
      const filtered = (data.faces || []).filter(
        (f) => w === 0 || f.faceRectangle.width / w >= 0.06,
      );
      setFaces(filtered);
      setBackendOnline(true);
      // Un nouveau visage vient d'être auto-enrôlé : rafraîchit la liste.
      if (filtered.some((f) => f.system_action === "Auto-enrôlé")) {
        void loadReferences();
      }
    } catch (err) {
      setBackendOnline(false);
      notify(`Analyse : ${(err as Error).message}`, "error");
    } finally {
      inFlightRef.current = false;
      setIsAnalyzing(false);
    }
  }, [notify, loadReferences]);

  // Au montage : santé + données initiales (récupération asynchrone légitime,
  // les setState surviennent après await — pas de rendu en cascade synchrone).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void Promise.all([checkHealth(), loadReferences(), loadHistory()]);
  }, [checkHealth, loadReferences, loadHistory]);

  // Boucle d'analyse
  useEffect(() => {
    if (!running) return;
    const id = setInterval(captureAndAnalyze, intervalMs);
    return () => clearInterval(id);
  }, [running, intervalMs, captureAndAnalyze]);

  // Rafraîchir l'historique périodiquement
  useEffect(() => {
    const id = setInterval(loadHistory, 5000);
    return () => clearInterval(id);
  }, [loadHistory]);

  // Health-check périodique + reconnexion auto (R15) : sonde le backend toutes
  // les 10 s. Quand il revient en ligne après une coupure, recharge les données.
  useEffect(() => {
    const id = setInterval(async () => {
      const wasOffline = backendOnline === false;
      try {
        const h = await api.health();
        setBackendOnline(true);
        if (wasOffline) {
          notify("Backend de nouveau en ligne.", "success");
          void loadReferences();
          void loadHistory();
          if (!h.azure_configured) {
            notify("Azure Face API non configuré côté backend.", "error");
          }
        }
      } catch {
        setBackendOnline(false);
      }
    }, 10000);
    return () => clearInterval(id);
  }, [backendOnline, notify, loadReferences, loadHistory]);

  const handleVideoLoad = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const v = e.currentTarget;
    const size = { width: v.videoWidth, height: v.videoHeight };
    cameraSizeRef.current = size;
    setCameraSize(size);
  };

  return (
    <main className="relative flex min-h-dvh flex-col items-center overflow-hidden py-10">
      <div className="pointer-events-none absolute left-[-10%] top-[-10%] h-[40%] w-[40%] rounded-full bg-amber-600/10 blur-[120px]" />
      <div className="pointer-events-none absolute bottom-[-10%] right-[-10%] h-[40%] w-[40%] rounded-full bg-indigo-600/10 blur-[120px]" />

      <div className="z-10 flex w-full max-w-6xl flex-col gap-8 px-6">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--color-border)] pb-6">
          <div className="flex items-center gap-3">
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 shadow-[0_0_15px_rgba(217,119,6,0.4)]">
              <Zap className="h-6 w-6 text-amber-400" aria-hidden="true" />
            </div>
            <div>
              <h1 className="bg-gradient-to-r from-amber-400 to-indigo-400 bg-clip-text text-2xl font-bold text-transparent">
                Cognitive Face Live
              </h1>
              <p className="text-sm text-slate-400">
                Reconnaissance faciale 1:N · Analyse de posture en temps réel
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-sm font-medium">
            <div className="flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  backendOnline === null
                    ? "bg-slate-500"
                    : backendOnline
                      ? "bg-emerald-400"
                      : "bg-rose-500 animate-pulse"
                }`}
                aria-hidden="true"
              />
              <span className="text-slate-300">
                {backendOnline === null
                  ? "Connexion…"
                  : backendOnline
                    ? "Backend en ligne"
                    : "Backend hors ligne"}
              </span>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2">
              <Activity
                className={`h-4 w-4 ${isAnalyzing ? "text-amber-400" : "text-slate-500"}`}
                aria-hidden="true"
              />
              <span className="text-slate-300">
                {isAnalyzing ? "Analyse…" : running ? "En attente" : "En pause"}
              </span>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <CameraView
              webcamRef={webcamRef}
              faces={faces}
              cameraSize={cameraSize}
              onVideoLoad={handleVideoLoad}
              isAnalyzing={isAnalyzing}
            />
          </div>

          <aside className="flex flex-col rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-lg">
            <div
              role="tablist"
              aria-label="Panneaux"
              className="mb-5 flex gap-1 rounded-lg bg-slate-900/60 p-1"
            >
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={tab === id}
                  onClick={() => setTab(id)}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-2 text-xs font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-400 ${
                    tab === id
                      ? "bg-slate-700 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  title={label}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  <span className="hidden sm:inline">{label}</span>
                </button>
              ))}
            </div>

            <div className="flex min-h-[24rem] flex-1 flex-col">
              {tab === "telemetry" && <TelemetryPanel faces={faces} />}
              {tab === "history" && <HistoryPanel events={events} />}
              {tab === "references" && (
                <ReferencesPanel
                  references={references}
                  onAdd={addReference}
                  onRename={renameReference}
                  onDelete={deleteReference}
                />
              )}
              {tab === "settings" && (
                <SettingsPanel
                  intervalMs={intervalMs}
                  onIntervalChange={setIntervalMs}
                  running={running}
                  onToggleRunning={() => setRunning((r) => !r)}
                />
              )}
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <ToastProvider>
      <Dashboard />
    </ToastProvider>
  );
}
