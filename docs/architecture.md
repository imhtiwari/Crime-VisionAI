# Architecture

CrimeVision AI separates the browser UI, Flask HTTP routes, persistence models, and media/model services.

```text
React + Vite
  └─ Axios → Flask /api/v1
                 ├─ routes: validation, serialization, status codes
                 ├─ services: media processing, Groq, PDF, evidence fusion inputs
                 ├─ SQLAlchemy → local SQLite
                 └─ backend/storage → originals, derivatives, reports
```

Uploads are validated before registering `Evidence` metadata and a SHA-256 digest. Original files remain in the upload store; annotated images, sampled frames, and PDFs have separate controlled locations. Analysis runs, detections, transcript segments, timeline events, persistent chat messages, jobs, report metadata, and audit events are relational records.

Video and audio tasks run in a bounded `ThreadPoolExecutor` for local development. Job state is persisted; on application restart, queued/running tasks are marked failed rather than falsely resumed. Video timestamps are relative to the media. No cross-file synchronization is inferred. The scene view projects image coordinates for illustration and does not claim depth.

Detection, captioning, and transcription adapters are optional and require local model weights. The Groq client reads credentials only in the backend and validates response structure and citations against retrieved database records. When a capability is unavailable, metadata workflows remain available and no synthetic findings are returned.

The current app is single-user and intended for localhost. Authentication, per-investigation authorization, migrations, a durable distributed job queue, and deployment hardening are future operational requirements.
