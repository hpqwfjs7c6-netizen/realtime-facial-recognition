import os
import base64
import requests
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

try:
    from deepface import DeepFace
except ImportError:
    DeepFace = None

# 1. Variables d'environnement
load_dotenv()

app = FastAPI(title="Real-time Facial Recognition API - DeepFace + HeadPose")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AZURE_FACE_ENDPOINT = os.getenv("AZURE_FACE_ENDPOINT")
AZURE_FACE_KEY = os.getenv("AZURE_FACE_KEY")

# Variables globales système et Azure
notepad_opened = False
REFERENCE_IMAGE_PATH = "reference.jpg"

class ImagePayload(BaseModel):
    image: str

def get_azure_headers():
    return {
        'Ocp-Apim-Subscription-Key': AZURE_FACE_KEY,
        'Content-Type': 'application/octet-stream'
    }

def detect_face(image_bytes: bytes):
    """Envoie l'image à l'API Azure pour détection et récupère le headPose."""
    # 1. Paramètres Azure : returnFaceId=false, returnFaceLandmarks=false, returnFaceAttributes=headPose
    url = f"{AZURE_FACE_ENDPOINT.rstrip('/')}/face/v1.0/detect?returnFaceId=false&returnFaceLandmarks=false&returnFaceAttributes=headPose&detectionModel=detection_03&recognitionModel=recognition_04"
    
    response = requests.post(url, headers=get_azure_headers(), data=image_bytes)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Erreur Azure Detect: {response.text}")
    
    return response.json()

@app.on_event("startup")
async def startup_event():
    """Vérification de la présence de DeepFace et de l'image de référence."""
    if not AZURE_FACE_ENDPOINT or not AZURE_FACE_KEY:
        print("ATTENTION: Clés Azure manquantes dans le .env !")
        
    if not os.path.exists(REFERENCE_IMAGE_PATH):
        print(f"ATTENTION: Fichier {REFERENCE_IMAGE_PATH} introuvable. La vérification DeepFace 1:1 ne pourra pas fonctionner.")
    else:
        print(f"SUCCÈS: Image de référence {REFERENCE_IMAGE_PATH} trouvée sur le disque.")
        
    if DeepFace is None:
        print("ATTENTION: La librairie DeepFace n'est pas installée. La reconnaissance faciale locale échouera. Installez-la avec 'pip install deepface'.")

@app.post("/analyze-face")
async def analyze_face(payload: ImagePayload):
    global notepad_opened
    
    if not AZURE_FACE_ENDPOINT or not AZURE_FACE_KEY:
        raise HTTPException(status_code=500, detail="L'Endpoint ou la clé Azure n'est pas configuré.")

    # Nettoyage du Base64
    image_data = payload.image.split(",")[1] if "," in payload.image else payload.image
    
    try:
        image_bytes = base64.b64decode(image_data)
        # On sauvegarde l'image capturée pour l'analyse locale par DeepFace
        temp_capture_path = "temp_capture.jpg"
        with open(temp_capture_path, "wb") as f:
            f.write(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de décodage base64 : {str(e)}")

    try:
        # Détection du visage capturé
        detect_result = detect_face(image_bytes)
        
        # Si aucun visage détecté : on réarme le système
        if len(detect_result) == 0:
            notepad_opened = False
            if os.path.exists(temp_capture_path):
                os.remove(temp_capture_path)
            return {"faces": []}
            
        captured_face = detect_result[0]
        face_rectangle = captured_face.get("faceRectangle", {})
        
        # 2. Extraction des angles
        head_pose = captured_face.get("faceAttributes", {}).get("headPose", {})
        pitch = head_pose.get("pitch", 0.0)
        roll = head_pose.get("roll", 0.0)
        yaw = head_pose.get("yaw", 0.0)
        
        recognized = False
        confidence = 0.0
        system_action = "None"
        
        # 3. Logique du Regard Direct
        looking_direct = (-15 <= pitch <= 15) and (-15 <= yaw <= 15)
        
        # 4. Flux d'exécution conditionnel
        if not looking_direct:
            # Ne lance PAS DeepFace.
            notepad_opened = False
            system_action = "User looking away"
            recognized = False
        else:
            # La condition est VRAIE : Lance la vérification DeepFace locale
            if os.path.exists(REFERENCE_IMAGE_PATH) and DeepFace is not None:
                try:
                    # enforce_detection=False car Azure a déjà validé la présence du visage
                    result = DeepFace.verify(
                        img1_path=REFERENCE_IMAGE_PATH,
                        img2_path=temp_capture_path,
                        enforce_detection=False
                    )
                    
                    is_identical = result.get("verified", False)
                    # Extraction basique d'une confidence inversée depuis la distance DeepFace
                    distance = result.get("distance", 1.0)
                    confidence = max(0.0, 1.0 - distance)
                    
                    if is_identical:
                        recognized = True
                        
                        # Si DeepFace confirme l'identité, déclenche l'automatisation
                        if not notepad_opened:
                            print("Visage reconnu (DeepFace) et regard direct ! Ouverture de Notepad...")
                            subprocess.Popen(["notepad.exe"])
                            notepad_opened = True
                            system_action = "Notepad opened"
                        else:
                            system_action = "Already open"
                    else:
                        notepad_opened = False
                        system_action = "Not recognized by DeepFace"
                except Exception as e:
                    print(f"Erreur interne DeepFace: {str(e)}")
                    notepad_opened = False
                    system_action = "DeepFace error"
            else:
                notepad_opened = False
                system_action = "DeepFace or reference missing"

        # Nettoyage
        if os.path.exists(temp_capture_path):
            os.remove(temp_capture_path)

        # 5. Retour API incluant pitch et yaw
        return {
            "faces": [
                {
                    "faceRectangle": {
                        "top": face_rectangle.get("top", 0),
                        "left": face_rectangle.get("left", 0),
                        "width": face_rectangle.get("width", 0),
                        "height": face_rectangle.get("height", 0)
                    },
                    "recognized": recognized,
                    "confidence": round(confidence, 2),
                    "pitch": pitch,
                    "yaw": yaw,
                    "roll": roll,
                    "system_action": system_action
                }
            ]
        }
            
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erreur réseau vers Azure: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur inattendue: {str(e)}")
