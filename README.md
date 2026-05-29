# Cognitive Face Live — Reconnaissance faciale temps réel

Tableau de bord de reconnaissance faciale **1:N** en temps réel : flux webcam,
détection de visages et analyse de posture (head-pose) via **Azure Face API**,
vérification biométrique locale via **DeepFace**, historique des reconnaissances
et gestion des visages de référence.

| Couche | Stack |
|--------|-------|
| Backend | Python · FastAPI · DeepFace · Azure Face API · SQLite |
| Frontend | Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · react-webcam |

---

## Architecture

```
Webcam ──► Frontend (capture périodique, anti-empilement)
              │  POST /analyze-face (base64)
              ▼
          Backend FastAPI
              ├─ Azure Face Detect ──► visages + head-pose (pitch/yaw/roll)
              ├─ si regard direct ──► DeepFace.verify contre chaque référence
              ├─ action configurable (log / commande / webhook)
              └─ persistance SQLite (références + historique)
```

### Fonctionnalités

- **Multi-visages** : tous les visages détectés sont analysés (plus seulement le premier).
- **Multi-références** : enrôlez plusieurs personnes ; la meilleure correspondance gagne.
- **Action configurable et cross-platform** : `log`, `command` ou `webhook`
  (remplace l'ancien `notepad.exe` Windows-only).
- **Historique persistant** : chaque événement est journalisé en base SQLite.
- **Enrôlement par upload** : ajout/suppression de visages depuis l'interface.
- **Réglages live** : intervalle de capture, pause/reprise.
- **Sécurité** : CORS restreint, clé API optionnelle, fichiers temporaires uniques.
- **Robustesse** : timeouts HTTP, fallback, logs structurés.

---

## Démarrage rapide (Docker)

```bash
cp backend/.env.example backend/.env   # renseignez vos clés Azure
docker compose up --build
```

- Frontend : http://localhost:3000
- Backend : http://localhost:8000 (docs interactives : http://localhost:8000/docs)

---

## Développement local

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # renseignez AZURE_FACE_ENDPOINT et AZURE_FACE_KEY
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # ajustez NEXT_PUBLIC_BACKEND_URL si besoin
npm run dev
```

---

## Configuration backend (`.env`)

| Variable | Description | Défaut |
|----------|-------------|--------|
| `AZURE_FACE_ENDPOINT` | Endpoint Azure Face | — |
| `AZURE_FACE_KEY` | Clé Azure Face | — |
| `HEADPOSE_PITCH_MAX` / `HEADPOSE_YAW_MAX` | Seuils du « regard direct » (°) | 15 |
| `DEEPFACE_MODEL` | Modèle DeepFace | VGG-Face |
| `RECOGNITION_ACTION` | `none` / `log` / `command` / `webhook` | log |
| `RECOGNITION_COMMAND` | Commande shell (`{name}`, `{confidence}`) | — |
| `RECOGNITION_WEBHOOK_URL` | URL POST appelée à la reconnaissance | — |
| `API_KEY` | Clé API (vide = auth désactivée) | — |
| `CORS_ORIGINS` | Origines autorisées (séparées par virgules) | http://localhost:3000 |

---

## API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/health` | État du service |
| `GET` | `/settings` | Seuils & config courante |
| `POST` | `/analyze-face` | Analyse une image (multi-visages) |
| `POST` | `/references` | Enrôle un visage (`name` + `file`) |
| `GET` | `/references` | Liste les références |
| `DELETE` | `/references/{id}` | Supprime une référence |
| `GET` | `/history?limit=N` | Historique des reconnaissances |

Si `API_KEY` est défini, passez l'en-tête `x-api-key` sur les routes protégées.

---

## Tests

```bash
cd backend && pytest -q        # backend (mocks Azure/DeepFace)
cd frontend && npx eslint src && npm run build   # frontend
```

L'intégration continue (`.github/workflows/ci.yml`) exécute ces vérifications
automatiquement sur chaque push et pull request.
