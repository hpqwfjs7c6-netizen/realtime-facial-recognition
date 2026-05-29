# CLAUDE.md — Cognitive Face Live

## Project overview

Real-time 1:N facial recognition dashboard. Webcam captures are periodically
sent to a FastAPI backend that uses Azure Face API (detection + head-pose) and
DeepFace (local verification against enrolled references). Results are shown
live on a Next.js frontend with bounding-box overlays.

## Repository layout

```
backend/          FastAPI app (Python)
  main.py         API routes
  recognition.py  Azure Face + DeepFace logic
  actions.py      Configurable post-recognition actions
  database.py     SQLite helpers (references + history)
  config.py       Settings (pydantic-settings, reads .env)
  tests/          pytest suite

frontend/         Next.js 16 / React 19 / TypeScript / Tailwind 4
  src/app/        page.tsx — main dashboard (client component)
  src/components/ CameraView, TelemetryPanel, HistoryPanel,
                  ReferencesPanel, SettingsPanel, Toast
  src/lib/        api.ts, types.ts
```

## Development commands

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload          # dev server on :8000
pytest                             # run tests
```

Requires a `backend/.env` (copy `backend/.env.example`):
```
AZURE_FACE_ENDPOINT=https://<resource>.cognitiveservices.azure.com
AZURE_FACE_KEY=<key>
```

### Frontend

```bash
cd frontend
npm ci
npm run dev                        # dev server on :3000
npm run build && npm start         # production build
```

### Docker (full stack)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Frontend: http://localhost:3000 — Backend: http://localhost:8000

## Key conventions

- **No Azure key?** Backend still starts; `/health` returns `azure_configured: false` and the frontend shows a toast warning.
- **Coordinate mapping**: screenshot is taken at the camera's intrinsic resolution (`forceScreenshotSourceSize`). Bounding boxes are expressed as percentages of that resolution and mapped 1:1 onto the video element (which uses `object-fill`, not `object-cover`).
- **Anti-stacking**: `inFlightRef` prevents concurrent `/analyze-face` calls; a new capture only fires when the previous one has completed.
- **Small-face filter**: faces whose width < 6 % of the frame are discarded (background TVs, reflections).
- **Mirrored video**: the webcam feed is mirrored for a natural selfie feel; Azure coordinates are in the *unmirrored* space, so the CSS `transform: scaleX(-1)` is applied only to the `<video>` element, not to the overlay container.

## Next.js version note

This project uses Next.js 16 / React 19. Read `frontend/AGENTS.md` before
modifying frontend code — APIs and conventions may differ from older versions.
