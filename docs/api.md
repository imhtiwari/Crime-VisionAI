# API reference

Base path: `/api/v1`. JSON errors use `{ "error": "…" }`. Uploads use `multipart/form-data` with a `file` field. IDs are opaque UUIDs.

## Health and dashboard

- `GET /health` — process health.
- `GET /capabilities` — configured modules, supported formats, and limits; never returns secrets.
- `GET /dashboard` — persisted counts, recent evidence/analyses/jobs, and activity.

## Evidence

- `POST /evidence/upload` — validates image/video/audio content, stores the original, records hash and media metadata (`201`; duplicate hash `409`).
- `GET /evidence?page=1&per_page=20&media_type=image&search=…&status=…` — paginated list.
- `GET /evidence/{id}` — metadata and analysis history.
- `GET /evidence/{id}/download` and `/preview` — controlled file delivery.
- `DELETE /evidence/{id}?confirm={id}` — explicit confirmation required; records deletion audit event.

## Analysis and jobs

- `POST /analysis/image/{id}` — optional `confidence_threshold` from 0 to 1. Returns image metadata, actual model detections (if available), caption status, and warnings.
- `POST /analysis/video/{id}` — optional `sampling_interval_seconds` integer from 1 to 600. Returns a queued job.
- `POST /analysis/audio/{id}` — queues transcription.
- `GET /analysis/{analysis_id}` — analysis and persisted findings.
- `GET /analysis/audio/{evidence_id}/transcript` — latest transcript segments and status.
- `GET /analysis/{analysis_id}/artifacts/{kind}` — controlled derivative download.
- `GET /jobs/{job_id}` — status, progress, and safe error detail.

Job statuses: `queued`, `running`, `completed`, `failed`, `cancelled`. Long work is performed by a local bounded background thread pool, not the request worker.

## Timeline

- `GET /timeline?evidence_id=…&source_type=…&category=…&after=ISO8601&before=ISO8601` — source-linked events.
- `POST /timeline/events` — investigator event with title, description, category; optional evidence/analysis link and explicit time fields.
- `PATCH /timeline/events/{id}` — edit permitted fields or set `verification_status` to `unverified`, `review_required`, or `verified`; audit history is recorded.

Times from media remain media-relative unless a reliable external timestamp was supplied. The API does not infer synchronization between files.

## Assistant and reports

- `POST /chat/conversations` — create persistent conversation.
- `GET /chat/conversations` and `GET /chat/conversations/{id}` — list/history.
- `POST /chat/conversations/{id}/messages` — `{ "message": "…", "evidence_ids": ["…"] }`; requires configured Groq key and model. Citations are retained only when they match retrieved records.
- `POST /reports` — `{ "title": "…", "evidence_ids": ["…"] }`; omit IDs to include up to 100 stored items.
- `GET /reports` and `GET /reports/{id}/download` — list and download generated PDF.

The local prototype does not enforce user authentication or multi-investigation access policies. Do not expose these endpoints to untrusted networks.
