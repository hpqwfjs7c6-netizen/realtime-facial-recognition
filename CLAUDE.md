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

## Security Hardening (2026-05 Sprint)

Implemented 7 CVE-class hardening measures across backend, Docker, and CI:

### 1. Input Validation & Limits (DoS Prevention)
- **backend/config.py**: Added `MAX_IMAGE_BYTES`, `MAX_UPLOAD_BYTES`, `HISTORY_LIMIT_MAX`
- **backend/main.py**: Image magic-byte detection before decoding (`_IMAGE_MAGIC`, `_looks_like_image()`)
- **backend/main.py**: Size validation in `_decode_image()` prevents memory exhaustion
- `.env.example`: Default limits: 8 MB images, 200-item history

### 2. Command Execution (RCE Prevention)
- **backend/config.py**: Added `ALLOW_COMMAND_ACTION` boolean (default `false`)
- **backend/actions.py**: Command execution blocked unless `ALLOW_COMMAND_ACTION=true`
- `.env.example`: Documented that commands require explicit trust-environment override

### 3. Production Mode & API Authentication
- **backend/config.py**: Added `ENV` setting (`development` | `production`)
- **backend/config.py**: `is_production()` classmethod enforces `API_KEY` requirement in prod
- **backend/main.py**: `lifespan()` raises early if production without API_KEY (fail-safe startup)
- `.env.example`: Documented that API_KEY is mandatory in production

### 4. Multi-Face Handling (Info Leak Prevention)
- **backend/main.py**: Each face in a frame gets its own cropped capture via `save_temp_capture(image_bytes, rect)`
- **backend/recognition.py**: `_crop_face_bytes(image_bytes, rect, padding=0.25)` extracts individual face region as JPEG
- Prevents accidental exposure of full frame when sharing/logging individual face results

### 5. Non-Root Docker Execution
- **backend/Dockerfile**: Added `gosu` (privilege-dropping utility)
- **backend/docker-entrypoint.sh** (new): Runs as root → fixes volume ownership → drops to appuser via gosu
- Handles pre-existing root-owned volumes from `docker compose up`
- Prevents container escape via elevated privileges

### 6. Cross-Platform Line Endings (Script Integrity)
- **.gitattributes** (new): Forces `*.sh` and `docker-entrypoint.sh` to LF line endings
- **backend/Dockerfile**: Sed-based CRLF cleanup as defense-in-depth
- Prevents shebang corruption on Windows git clones

### 7. Dependency Audit in CI
- **.github/workflows/ci.yml**: Added `audit` job running `pip-audit` and `npm audit`
- Detects vulnerable transitive dependencies before merge

---

## Auto-Enrollment Feature (2026-05 Sprint)

Allows automatic registration of clearly-detected faces with optional user renaming.

### Database Schema (backend/database.py)

Added to `references_face` table:
- `auto INTEGER` — 1 if auto-enrolled, 0 if manually named (marks enrollment mode)
- Migration logic checks for existing column before ALTER (idempotent)
- New `meta` table tracks `next_auto_label` counter for "Visage N" naming

### Recognition Flow (backend/main.py)

1. **Pose Clarity Check**: `is_clear_for_enrollment(pitch, yaw, roll)` verifies strict thresholds:
   - Pitch ≤ `AUTO_ENROLL_PITCH_MAX` (default 8°)
   - Yaw ≤ `AUTO_ENROLL_YAW_MAX` (default 8°)
   - Roll ≤ `AUTO_ENROLL_ROLL_MAX` (default 12°)

2. **Size Filter**: Face width ≥ `AUTO_ENROLL_MIN_WIDTH_RATIO` (default 8% of frame)
   - Prevents tiny/blurry faces from being enrolled

3. **Non-Matching**: DeepFace.verify returns False (face not in references)

4. **Auto-Enrollment Trigger**: `_maybe_auto_enroll()` registers face as "Visage N"
   - Cropped face stored via `save_reference_image()`
   - System action set to `"Auto-enrôlé"` in response

### Frontend Updates (frontend/src/components/ReferencesPanel.tsx)

- **ReferenceRow**: Inline edit with Enter/Escape, Check/X confirm buttons
- **Thumbnail**: Async loading from `api.referenceImageUrl(id)` with URL cleanup
- **Auto Badge**: Amber Sparkles icon + "auto" label on auto-enrolled faces
- **Rename Flow**: Click pencil → edit name → press Enter/Click Check → system clears auto flag
- Helper text explains auto-enrollment behavior and renaming

### Frontend API (frontend/src/lib/api.ts)

- `updateReference(id, name)` — PATCH endpoint to rename
- `referenceImageUrl(id)` — GET endpoint returning object URL blob for thumbnail display
- Both include auth headers if API_KEY is set

### Environment Variables (.env.example)

```
AUTO_ENROLL=true
AUTO_ENROLL_PITCH_MAX=8       # Max head pitch for clear enrollment
AUTO_ENROLL_YAW_MAX=8         # Max head yaw
AUTO_ENROLL_ROLL_MAX=12       # Max head roll
AUTO_ENROLL_MIN_WIDTH_RATIO=0.08  # Min face width ratio
```

### Testing (backend/tests/test_api.py)

- `test_auto_enroll_unknown_clear_face()`: Verify auto-enrollment on clear unrecognized faces
- `test_auto_enroll_disabled()`: Verify AUTO_ENROLL=false blocks enrollment
- `test_rename_reference()`: PATCH endpoint 200/404 cases
- `test_reference_image_endpoint()`: GET /references/{id}/image 200/404 cases

---

## Docker Volume Permission Fix (2026-05)

### Problem
Non-root hardening (dropping to `appuser`) prevented writing to volumes owned by root.

### Solution
- **docker-entrypoint.sh**: Runs as root, fixes ownership of `/app/data` via `chown`, then execs `gosu appuser`
- **Dockerfile**: Changed `USER appuser` to `ENTRYPOINT ["/docker-entrypoint.sh"]`
- Handles both fresh and pre-existing root-owned volumes

### CRLF Issue
Windows git clones converted `docker-entrypoint.sh` to CRLF, breaking the shebang.
- Fix 1: `.gitattributes` forces LF for all `*.sh` files
- Fix 2: Dockerfile sed clears CRLF as defense-in-depth
