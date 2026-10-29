# CrimeVision AI

CrimeVision AI is a multimodal forensic analysis prototype. It stores uploaded evidence and generated analyses in SQLite and local storage, and presents them through a React dashboard. Findings are preliminary decision-support material and require human review.

## Deployment

For production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md) for instructions on deploying to Render (backend) and Vercel (frontend).

## Current capabilities

- **Evidence Vault:** image, video, and audio uploads; content validation; SHA-256 hashes; duplicate detection; persistent metadata; preview/download; confirmed deletion with audit record.
- **Images:** dimensions/format metadata, optional local RT-DETR detection, optional local BLIP captioning, annotated derivatives, confidence threshold, and explicit unavailable status when no model is installed.
- **Video:** OpenCV validation, background frame sampling, media-relative timestamps, per-frame detections when a detector is available, saved sampled frames, and persistent job progress. This is sampled-frame analysis, not action recognition.
- **Audio:** WAV validation and background Faster-Whisper transcription with timestamped segments when Faster-Whisper and local model weights are configured. MP3/M4A/FLAC/OGG decoding requires PyAV. Transcripts remain separate from generated summaries.
- **Timeline:** persistent upload, analysis, and transcript records plus investigator annotations; filters and review status changes are audit logged. Media-relative timing is not synchronized across files.
- **Assistant:** persistent conversations and evidence-grounded Groq responses, with schema validation and server-side citation checks. Requires `GROQ_API_KEY` and `GROQ_MODEL`.
- **Reports:** downloadable record-derived PDF reports. ReportLab is the preferred renderer; a small built-in text PDF renderer keeps report generation available when that optional dependency is missing.
- **3D scene view:** interactive illustrative projection of real 2D detections. It does not estimate accurate physical depth or scene geometry.
- **Dashboard:** real persisted counts, recent activity, recent jobs, media type counts, and timeline activity.

No detections, captions, transcripts, or assistant answers are fabricated when a model is unavailable. The default install does not download large model weights. General pretrained detectors only identify their supported classes and cannot be assumed to identify weapons or other forensic traces.

## Requirements

- Python 3.9 or later (the current environment was verified with Python 3.13.2)
- Node.js 18 or later
- Windows PowerShell, macOS, or Linux
- Optional: local RT-DETR weights and PyTorch/Transformers; Faster-Whisper model files; Groq API credentials

## Run on Windows

In one PowerShell terminal:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

If PowerShell blocks activation, either run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` for that terminal, or run the venv interpreter directly: `.venv\Scripts\python.exe run.py`.

In a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` calls to `http://127.0.0.1:5000`; the frontend never receives the Groq secret. The API base can be set with `VITE_API_BASE_URL` when using a different setup.

## Optional AI services

Configure these in `backend/.env`; do not put secrets in frontend variables:

```dotenv
GROQ_API_KEY=your_key_here
GROQ_MODEL=your_supported_model_name
```

For local object detection, install `backend/requirements-vision.txt`, then set `DETECTION_MODEL_PATH` to a local Transformers RT-DETR directory containing its config, weights, and processor config. The adapter loads local files only. For local captioning, set `CAPTION_MODEL_PATH` to a local BLIP directory. For speech transcription, install `backend/requirements-audio.txt` and set `WHISPER_MODEL_PATH` to a local Faster-Whisper model directory. Audio model downloads are disabled unless explicitly enabled with `ALLOW_MODEL_DOWNLOAD=true`.

`GET /api/v1/capabilities` reports what is configured. If the model runtime or weights are absent, the corresponding feature reports unavailable and the rest of the app remains usable.

## Tests and checks

Backend API tests use `unittest` (also discoverable by pytest):

```powershell
cd backend
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Frontend type check and production build:

```powershell
cd frontend
npm run build
```

## API overview

All API routes are under `/api/v1`. See [docs/api.md](docs/api.md) for the request and response outline.

- `GET /health`, `GET /capabilities`, `GET /dashboard`
- `POST /evidence/upload`, `GET /evidence`, `GET /evidence/{id}`, `GET /evidence/{id}/download`, `GET /evidence/{id}/preview`, `DELETE /evidence/{id}?confirm={id}`
- `POST /analysis/image/{id}`, `POST /analysis/video/{id}`, `POST /analysis/audio/{id}`, `GET /analysis/{id}`, `GET /analysis/audio/{id}/transcript`, `GET /jobs/{id}`
- `GET /timeline`, `POST /timeline/events`, `PATCH /timeline/events/{id}`
- `POST /chat/conversations`, `GET /chat/conversations`, `GET /chat/conversations/{id}`, `POST /chat/conversations/{id}/messages`
- `POST /reports`, `GET /reports`, `GET /reports/{id}/download`

## Storage and security

SQLite, uploaded originals, generated frame images, annotated derivatives, and PDFs are stored under `backend/` by default. Original evidence bytes are kept separate from generated derivatives. SHA-256 hashes identify the uploaded bytes recorded by this app; they do not establish authenticity or completeness. Uploads are type/content validated, assigned internal names, bounded by `MAX_UPLOAD_SIZE`, and stored outside the frontend's public assets.

This is a local single-user prototype. It does not implement login, multi-user authorization, or case-level access controls; keep it bound to localhost and do not expose it to a network until authentication and authorization are added. API changes and deletion operations are logged where implemented. Treat uploaded files and transcripts as untrusted. Validate this application and its models before operational forensic use.

## Known limitations

- No model weights or Groq key are bundled. Image detection, captioning, transcription, and LLM reasoning depend on configuration.
- Video processing is background-thread based for a single local process; job records survive restarts, but interrupted jobs are marked failed. It is not a distributed queue.
- No action-recognition, diarization, calibrated depth reconstruction, automatic clock synchronization, or verified crime classification is implemented.
- Codec support depends on OpenCV and optional PyAV availability; capability output lists current supported formats.
- SQLite schema initialization uses SQLAlchemy `create_all`; a migration framework is not yet configured.
- Local unauthenticated operation is for development only.
