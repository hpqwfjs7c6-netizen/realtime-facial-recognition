"use client";

import React from "react";
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
  return (
    <section className="flex flex-col gap-4" aria-label="Flux caméra">
      <div className="relative aspect-video overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-2xl">
        <Webcam
          ref={webcamRef}
          audio={false}
          screenshotFormat="image/jpeg"
          screenshotQuality={0.7}
          videoConstraints={{ facingMode: "user", width: 1280, height: 720 }}
          onLoadedData={onVideoLoad}
          className="h-full w-full object-cover"
          aria-label="Flux vidéo en direct de la webcam"
        />

        {cameraSize.width > 0 &&
          faces.map((face, index) => {
            const r = face.faceRectangle;
            const left = (r.left / cameraSize.width) * 100;
            const top = (r.top / cameraSize.height) * 100;
            const width = (r.width / cameraSize.width) * 100;
            const height = (r.height / cameraSize.height) * 100;
            const border = face.recognized
              ? "border-emerald-400"
              : "border-rose-500";
            const shadow = face.recognized
              ? "shadow-[0_0_15px_rgba(16,185,129,0.5)]"
              : "shadow-[0_0_15px_rgba(239,68,68,0.5)]";
            return (
              <div
                key={`face-${index}`}
                className={`absolute rounded-lg border-2 transition-all duration-300 ${border} ${shadow}`}
                style={{
                  left: `${left}%`,
                  top: `${top}%`,
                  width: `${width}%`,
                  height: `${height}%`,
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
