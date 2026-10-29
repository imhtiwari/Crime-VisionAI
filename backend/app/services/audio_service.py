import importlib.util
import threading
from pathlib import Path

from app.config import settings


class AudioService:
    """Faster-Whisper adapter with explicit local-weight/download controls."""

    def __init__(self):
        self._model = None
        self._lock = threading.Lock()

    @property
    def model_source(self):
        if settings.WHISPER_MODEL_PATH:
            return settings.WHISPER_MODEL_PATH
        return settings.WHISPER_MODEL

    @property
    def status(self):
        if not importlib.util.find_spec('faster_whisper'):
            return 'model_unavailable'
        if settings.WHISPER_MODEL_PATH:
            model_path = Path(settings.WHISPER_MODEL_PATH)
            return 'ready' if model_path.is_dir() and (model_path / 'model.bin').is_file() and (model_path / 'config.json').is_file() else 'model_unavailable'
        return 'ready' if settings.ALLOW_MODEL_DOWNLOAD and bool(settings.WHISPER_MODEL) else 'model_not_configured'

    def _load_model(self):
        if self.status != 'ready':
            raise RuntimeError(self.status)
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from faster_whisper import WhisperModel
                    self._model = WhisperModel(self.model_source, device=settings.WHISPER_DEVICE, compute_type='int8')
        return self._model

    def transcribe(self, audio_path):
        model = self._load_model()
        segments, info = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)
        transcript_segments = []
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
            transcript_segments.append({
                'start_seconds': max(0.0, float(segment.start)),
                'end_seconds': max(float(segment.start), float(segment.end)),
                'text': text,
            })
        return {
            'language': getattr(info, 'language', None),
            'language_probability': getattr(info, 'language_probability', None),
            'duration_seconds': getattr(info, 'duration', None),
            'segments': transcript_segments,
        }


audio_service = AudioService()
