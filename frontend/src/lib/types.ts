export interface FaceRectangle {
  top: number;
  left: number;
  width: number;
  height: number;
}

export interface FaceData {
  faceRectangle: FaceRectangle;
  recognized: boolean;
  confidence: number;
  name: string | null;
  pitch: number;
  yaw: number;
  roll: number;
  system_action: string;
}

export interface ReferenceFace {
  id: number;
  name: string;
  image_path: string;
  created_at?: string;
}

export interface RecognitionEvent {
  id: number;
  name: string | null;
  recognized: boolean;
  confidence: number;
  pitch: number | null;
  yaw: number | null;
  roll: number | null;
  system_action: string | null;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  azure_configured: boolean;
  deepface_available: boolean;
  references: number;
  recognition_action: string;
}
