"use client";

import React, { useEffect, useRef, useState } from "react";
import Webcam from "react-webcam";
import { Camera, ShieldAlert } from "lucide-react";
import type { FaceData } from "@/lib/types";

interface Props {
  webcamRef: React.RefObject<Webcam | null>;
  faces: FaceData[];
  cameraSize: { width: number; height: number };
  onVideoLoad: (e: React.SyntheticEvent<HTMLVideoElement>) => void;
  isAnalyzing: boolean;
}

export default function CameraView({
  webcamRef,
  faces,
  cameraSize,
  onVideoLoad,
  isAnalyzing,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState({ width: 0, height: 0 });

  // Mesure la taille rendue du conteneur (pour mapper correctement object-cover).
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () =>
      setBox({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Conversion d'un rectangle (en pixels vidéo intrinsèques) vers les pixels
  // affichés, en compensant le rognage object-cover (échelle + recentrage).
  const mapRect = (r: FaceData["faceRectangle"]) => {
    const vw = cameraSize.width;
    const vh = cameraSize.height;
    const cw = box.width;
    const ch = box.height;
    if (!vw || !vh || !cw || !ch) return null;
    const scale = Math.max(cw / vw, ch / vh);
    const offsetX = (vw * scale - cw) / 2;
    const offsetY = (vh * scale - ch) / 2;
    return {
      left: r.left * scale - offsetX,
      top: r.top * scale - offsetY,
      width: r.width * scale,
      height: r.height * scale,
    };
  };

  return (
    <section className="flex flex-col gap-4" aria-label="Flux caméra">
      <div
        ref={containerRef}
        className="relative aspect-video overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl"
      >
        <Webcam
          ref={webcamRef}
          audio={false}
          screenshotFormat="image/jpeg"
          screenshotQuality={0.7}
          forceScreenshotSourceSize
          videoConstraints={{ facingMode: "user", width: 1280, height: 720 }}
          onLoadedData={onVideoLoad}
          className="h-full w-full object-cover"
          aria-label="Flux vidéo en direct de la webcam"
        />

        {faces.map((face, index) => {
          const rect = mapRect(face.faceRectangle);
          if (!rect) return null;
          const border = face.recognized
            ? "border-emerald-400"
            : "border-rose-500";
          const shadow = face.recognized
            ? "shadow-[0_0_15px_rgba(16,185,129,0.5)]"
            : "shadow-[0_0_15px_rgba(239,68,68,0.5)]";
          return (
            <div
              key={`face-${index}`}
              className={`pointer-events-none absolute rounded-lg border-2 transition-all duration-300 ${border} ${shadow}`}
              style={{
                left: `${rect.left}px`,
                top: `${rect.top}px`,
                width: `${rect.width}px`,
                height: `${rect.height}px`,
              }}
            >
              <div className="absolute left-1/2 top-[-35px] flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full border border-[var(--color-border)] bg-slate-900/90 px-3 py-1 text-sm font-semibold shadow-lg backdrop-blur-sm">
                <span
                  className={
                    face.recognized ? "text-emerald-400" : "text-rose-400"
                  }
                >
                  {face.recognized ? face.name || "Reconnu" : "Inconnu"}
                </span>
                <span className="font-mono text-xs text-slate-400">
                  {(face.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          );
        })}

        <div className="absolute bottom-4 left-4 flex items-center gap-2 rounded-lg border border-white/10 bg-black/50 px-3 py-1.5 text-xs font-medium backdrop-blur-md">
          <Camera className="h-4 w-4 text-slate-300" aria-hidden="true" />
          <span>{isAnalyzing ? "Analyse…" : "Flux actif"}</span>
        </div>
      </div>

      <p className="flex items-center gap-2 text-sm text-slate-500">
        <ShieldAlert className="h-4 w-4" aria-hidden="true" />
        Vérification locale (DeepFace). Regardez l&apos;écran pour déclencher
        l&apos;authentification biométrique.
      </p>
    </section>
  );
}
