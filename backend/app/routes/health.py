import importlib.util

from flask import Blueprint, jsonify
from app.config import settings
from app.services.audio_service import audio_service
from app.services.caption_service import caption_service
from app.services.detection_service import detection_service
from app.services.llm_service import llm_service
from app.utils.file_utils import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

try:
    import reportlab  # noqa: F401
    REPORTS_STATUS = 'available'
except ImportError:
    REPORTS_STATUS = 'available_fallback_renderer'

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'CrimeVision AI Backend',
        'version': '0.1.0',
        'environment': settings.FLASK_ENV
    }), 200


@health_bp.route('/capabilities', methods=['GET'])
def capabilities():
    """Return system capabilities and configuration status."""
    return jsonify({
        'status': 'operational',
        'modules': {
            'image_analysis': 'metadata_and_detection' if detection_service.status == 'ready' else 'metadata_only',
            'object_detection': detection_service.status,
            'image_captioning': caption_service.status,
            'video_analysis': 'frame_sampling_available',
            'audio_transcription': audio_service.status,
            'llm_reasoning': llm_service.status,
            'report_generation': REPORTS_STATUS,
            'timeline': 'available',
            'background_jobs': 'available'
        },
        'models': {
            'detection': detection_service.model_name,
            'whisper': settings.WHISPER_MODEL if audio_service.status == 'ready' else None,
            'captioning': caption_service.model_name,
            'groq': settings.GROQ_MODEL if llm_service.status == 'configured' else None
        },
        'supported_formats': {
            'images': sorted(IMAGE_EXTENSIONS),
            'videos': sorted(VIDEO_EXTENSIONS),
            'audio': sorted(AUDIO_EXTENSIONS) if importlib.util.find_spec('av') else ['wav']
        },
        'limits': {
            'max_upload_size_mb': settings.MAX_UPLOAD_SIZE // (1024 * 1024),
            'max_video_duration_seconds': settings.MAX_VIDEO_DURATION,
            'max_concurrent_jobs': settings.MAX_CONCURRENT_JOBS
        }
    }), 200
