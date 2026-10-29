import hashlib
import importlib.util
import os
import uuid
import wave
from pathlib import Path

import cv2
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}
VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
AUDIO_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac', 'ogg'}


def get_media_type(filename):
    extension = Path(filename).suffix.lower().lstrip('.')
    if extension in IMAGE_EXTENSIONS:
        return 'image'
    if extension in VIDEO_EXTENSIONS:
        return 'video'
    if extension in AUDIO_EXTENSIONS:
        return 'audio'
    return None


def allowed_file(filename, media_type=None):
    detected_type = get_media_type(filename)
    return detected_type is not None and (media_type is None or media_type == detected_type)


def calculate_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as file_handle:
        for byte_block in iter(lambda: file_handle.read(1024 * 1024), b''):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def generate_internal_filename(original_filename):
    extension = Path(original_filename).suffix.lower()
    return f'{uuid.uuid4()}{extension}'


def validate_image(file_path):
    """Verify image bytes and read only basic technical metadata."""
    try:
        with Image.open(file_path) as image:
            image_format = image.format
            width, height = image.size
            if image_format not in {'PNG', 'JPEG', 'BMP', 'WEBP'}:
                return False, None
            image.verify()
        return True, {'format': image_format, 'width': width, 'height': height}
    except (UnidentifiedImageError, OSError, ValueError):
        return False, None


def validate_video(file_path):
    """Open the container and decode a frame before accepting the video."""
    capture = cv2.VideoCapture(str(file_path))
    try:
        if not capture.isOpened():
            return False, None
        ok, frame = capture.read()
        if not ok or frame is None:
            return False, None
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 and frame_count > 0 else None
        return True, {
            'fps': fps if fps > 0 else None,
            'frame_count': frame_count if frame_count > 0 else None,
            'width': width,
            'height': height,
            'duration_seconds': duration,
        }
    finally:
        capture.release()


def validate_audio(file_path):
    """Validate WAV directly; validate other codecs only when PyAV is installed."""
    extension = Path(file_path).suffix.lower()
    if extension == '.wav':
        try:
            with wave.open(str(file_path), 'rb') as audio_file:
                channels = audio_file.getnchannels()
                sample_rate = audio_file.getframerate()
                frame_count = audio_file.getnframes()
                if channels < 1 or sample_rate < 1 or frame_count < 1:
                    return False, None
                return True, {
                    'format': 'wav',
                    'channels': channels,
                    'sample_rate': sample_rate,
                    'duration_seconds': frame_count / sample_rate,
                }
        except (wave.Error, EOFError, OSError):
            return False, None

    if not importlib.util.find_spec('av'):
        return False, None
    try:
        import av
        with av.open(os.fspath(file_path)) as container:
            stream = next((stream for stream in container.streams if stream.type == 'audio'), None)
            if stream is None:
                return False, None
            first_frame = next(container.decode(stream), None)
            if first_frame is None:
                return False, None
            duration = float(stream.duration * stream.time_base) if stream.duration and stream.time_base else None
            return True, {
                'format': container.format.name,
                'channels': len(first_frame.layout.channels),
                'sample_rate': first_frame.sample_rate,
                'duration_seconds': duration,
            }
    except Exception:
        return False, None
