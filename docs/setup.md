# Setup and troubleshooting

## Windows PowerShell

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

If activation is blocked, use `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`, or invoke `.venv\Scripts\python.exe run.py` without activating.

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Set `GROQ_API_KEY` and `GROQ_MODEL` only in `backend/.env`. Health/capability endpoints report missing optional services without preventing startup. The default model configuration does not download weights.

## Optional model runtimes

- Vision runtime: `pip install -r requirements-vision.txt`; provide local RT-DETR files via `DETECTION_MODEL_PATH`, and optionally local BLIP files via `CAPTION_MODEL_PATH`.
- Audio runtime: `pip install -r requirements-audio.txt`; provide a local Faster-Whisper model directory via `WHISPER_MODEL_PATH`.
- Audio file support beyond WAV requires PyAV and a codec it can decode. See `/api/v1/capabilities` for formats available in the running environment.

Model and native dependency sizes vary by hardware and platform. Ordinary unit tests do not download weights or call Groq.

## Verify

```powershell
cd backend
.venv\Scripts\python.exe -m unittest discover -s tests -v
cd ..\frontend
npm run build
```

The API is normally at `http://127.0.0.1:5000/api/v1/health` and the frontend at `http://localhost:5173`.

## Common issues

- **Groq unavailable:** confirm both backend variables are set; restart Flask after editing `.env`.
- **Detector/captioner unavailable:** verify local model path and expected Transformers files; this adapter loads local files only.
- **Transcription unavailable:** install the optional audio requirements and configure local model weights.
- **Video rejected:** verify OpenCV can decode the uploaded container/codec; supported formats depend on its build.
- **Port conflict:** change `PORT` in `backend/.env`; edit `frontend/vite.config.ts` for Vite's port/proxy.
- **Upload rejected:** check size limit, extension and actual media contents. Hashes represent file bytes as received, not authenticity.
