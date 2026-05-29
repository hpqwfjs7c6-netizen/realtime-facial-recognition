"use client";

import React, { useRef, useState, useCallback, useEffect } from "react";
import Webcam from "react-webcam";
import { Camera, RefreshCw, Zap, ShieldAlert, Cpu } from "lucide-react";

// Types correspondant au backend mis à jour
interface FaceRectangle {
  top: number;
  left: number;
  width: number;
  height: number;
}

interface FaceData {
  faceRectangle: FaceRectangle;
  recognized: boolean;
  confidence: number;
  pitch: number;
  yaw: number;
  roll: number;
  system_action: string;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const CAPTURE_INTERVAL_MS = 3000;

export default function Home() {
  const webcamRef = useRef<Webcam>(null);
  const [faces, setFaces] = useState<FaceData[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameraSize, setCameraSize] = useState({ width: 0, height: 0 });

  const captureAndAnalyze = useCallback(async () => {
    if (!webcamRef.current) return;
    
    // Capturer la frame de la vidéo
    const imageSrc = webcamRef.current.getScreenshot();
    if (!imageSrc) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_URL}/analyze-face`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ image: imageSrc }),
      });

      if (!response.ok) {
        let errorMessage = response.statusText;
        try {
            const errorData = await response.json();
            if (errorData && errorData.detail) {
                errorMessage = errorData.detail;
            }
        } catch (e) {
            // Si la réponse n'est pas du JSON, on garde statusText
        }
        throw new Error(`Erreur API: ${errorMessage}`);
      }

      const data = await response.json();
      setFaces(data.faces || []);
    } catch (err) {
      console.error("Erreur lors de l'analyse:", err);
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  // Déclencher l'analyse toutes les 3 secondes
  useEffect(() => {
    const intervalId = setInterval(() => {
      captureAndAnalyze();
    }, CAPTURE_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [captureAndAnalyze]);

  // Récupérer la taille réelle de la vidéo pour le calcul des bounding boxes
  const handleVideoLoad = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget;
    setCameraSize({
      width: video.videoWidth,
      height: video.videoHeight,
    });
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center py-10 relative overflow-hidden">
      
      {/* Background gradients for aesthetics */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] pointer-events-none" />

      <div className="z-10 w-full max-w-5xl px-6 flex flex-col gap-8">
        
        {/* Header */}
        <header className="flex items-center justify-between border-b border-slate-800 pb-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-500/10 rounded-xl border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.5)]">
              <Zap className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
                Cognitive Face Live
              </h1>
              <p className="text-sm text-slate-400">Vérification 1:1 Locale et Analyse de Posture</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4 text-sm font-medium">
             <div className="flex items-center gap-2 px-4 py-2 bg-slate-900 rounded-full border border-slate-800">
                <div className={`w-2 h-2 rounded-full ${isAnalyzing ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`} />
                <span className="text-slate-300">
                  {isAnalyzing ? "Analyse en cours..." : "En attente"}
                </span>
             </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Camera View */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-slate-900 shadow-2xl group aspect-video">
              
              {/* Webcam Component */}
              <Webcam
                ref={webcamRef}
                audio={false}
                screenshotFormat="image/jpeg"
                videoConstraints={{ facingMode: "user" }}
                onLoadedData={handleVideoLoad}
                className="w-full h-full object-cover"
              />

              {/* Bounding Boxes Overlay */}
              {cameraSize.width > 0 && faces.map((face, index) => {
                const rect = face.faceRectangle;
                const leftPercent = (rect.left / cameraSize.width) * 100;
                const topPercent = (rect.top / cameraSize.height) * 100;
                const widthPercent = (rect.width / cameraSize.width) * 100;
                const heightPercent = (rect.height / cameraSize.height) * 100;

                const borderColor = face.recognized ? "border-emerald-400" : "border-rose-500";
                const shadowColor = face.recognized ? "shadow-[0_0_15px_rgba(52,211,153,0.5)]" : "shadow-[0_0_15px_rgba(244,63,94,0.5)]";

                return (
                  <div
                    key={`face-${index}`}
                    className={`absolute border-2 ${borderColor} ${shadowColor} transition-all duration-300 rounded-lg`}
                    style={{
                      left: `${leftPercent}%`,
                      top: `${topPercent}%`,
                      width: `${widthPercent}%`,
                      height: `${heightPercent}%`,
                    }}
                  >
                    {/* Badge Résultat */}
                    <div className="absolute top-[-35px] left-1/2 -translate-x-1/2 bg-slate-900/90 backdrop-blur-sm border border-slate-700 px-3 py-1 rounded-full text-sm font-semibold whitespace-nowrap shadow-lg flex items-center gap-2">
                      <span className={face.recognized ? "text-emerald-400" : "text-rose-400"}>
                        {face.recognized ? "Reconnu (1:1)" : "Inconnu"}
                      </span>
                      <span className="text-slate-400 text-xs">{(face.confidence * 100).toFixed(0)}%</span>
                    </div>
                    
                    {/* UI Corners for techy look */}
                    <div className={`absolute -top-1 -left-1 w-3 h-3 border-t-2 border-l-2 ${borderColor}`} />
                    <div className={`absolute -top-1 -right-1 w-3 h-3 border-t-2 border-r-2 ${borderColor}`} />
                    <div className={`absolute -bottom-1 -left-1 w-3 h-3 border-b-2 border-l-2 ${borderColor}`} />
                    <div className={`absolute -bottom-1 -right-1 w-3 h-3 border-b-2 border-r-2 ${borderColor}`} />
                  </div>
                );
              })}

              {/* Status Overlay */}
              <div className="absolute bottom-4 left-4 flex items-center gap-2 px-3 py-1.5 bg-black/50 backdrop-blur-md rounded-lg text-xs font-medium border border-white/10">
                <Camera className="w-4 h-4 text-slate-300" />
                <span>Flux Actif</span>
              </div>
            </div>

            <p className="text-sm text-slate-500 flex items-center gap-2">
               <ShieldAlert className="w-4 h-4" /> 
               Vérification locale (DeepFace). L'authentification biométrique requiert que vous regardiez l'écran.
            </p>
          </div>

          {/* Sidebar / Results Data */}
          <div className="flex flex-col gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 h-full shadow-lg flex flex-col">
              <div className="flex items-center gap-3 mb-6">
                 <Cpu className="w-5 h-5 text-purple-400" />
                 <h2 className="text-lg font-semibold text-slate-200">Télémétrie & HeadPose</h2>
              </div>

              {faces.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-sm gap-4">
                  <RefreshCw className="w-8 h-8 animate-spin-slow opacity-50" />
                  <p>En attente d'un visage...</p>
                </div>
              ) : (
                <div className="flex flex-col gap-6 overflow-y-auto pr-2 custom-scrollbar">
                  {faces.map((face, index) => {
                    const lookingDirect = face.pitch >= -15 && face.pitch <= 15 && face.yaw >= -15 && face.yaw <= 15;

                    return (
                      <div key={`telemetry-${index}`} className="flex flex-col gap-4 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-semibold text-slate-200">Visage #{index + 1}</span>
                          <span className={`text-xs px-2 py-1 rounded font-medium ${face.recognized ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                            {face.recognized ? "Authentifié" : "Non Reconnu"}
                          </span>
                        </div>
                        
                        <div className="flex flex-col gap-2">
                            <div className="flex justify-between text-xs text-slate-400">
                                <span>Action Système :</span>
                                <span className="font-mono text-amber-400">{face.system_action}</span>
                            </div>
                            <div className="flex justify-between text-xs text-slate-400">
                                <span>Regard (Direct) :</span>
                                <span className={`font-bold ${lookingDirect ? "text-emerald-400" : "text-rose-400"}`}>
                                    {lookingDirect ? "OUI" : "NON (Regarde ailleurs)"}
                                </span>
                            </div>
                        </div>

                        <div className="pt-2 border-t border-slate-700/50">
                            <p className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wider">Angles de Tête (Azure)</p>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                                <div className="bg-slate-900 p-2 rounded flex flex-col">
                                    <span className="text-slate-500">Pitch (Haut/Bas)</span>
                                    <span className="font-mono text-slate-300">{face.pitch.toFixed(1)}°</span>
                                </div>
                                <div className="bg-slate-900 p-2 rounded flex flex-col">
                                    <span className="text-slate-500">Yaw (Gauche/Droite)</span>
                                    <span className="font-mono text-slate-300">{face.yaw.toFixed(1)}°</span>
                                </div>
                                <div className="bg-slate-900 p-2 rounded flex flex-col col-span-2">
                                    <span className="text-slate-500">Roll (Inclinaison)</span>
                                    <span className="font-mono text-slate-300">{face.roll.toFixed(1)}°</span>
                                </div>
                            </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
          
        </div>
      </div>
    </main>
  );
}
