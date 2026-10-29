import importlib.util
import json
import threading
from pathlib import Path

from app.config import settings


class DetectionService:
    """Optional RT-DETR adapter that only loads explicitly local model weights."""

    def __init__(self):
        self.model_path = settings.DETECTION_MODEL_PATH.strip()
        self.model_name = settings.DETECTION_MODEL.strip() or (Path(self.model_path).name if self.model_path else None)
        self.model = None
        self.processor = None
        self._lock = threading.Lock()

    @property
    def status(self):
        if not self.model_path:
            return 'model_not_configured' if not settings.DETECTION_MODEL else 'model_unavailable'
        if not Path(self.model_path).is_dir():
            return 'model_unavailable'
        if not importlib.util.find_spec('torch') or not importlib.util.find_spec('transformers'):
            return 'model_unavailable'
        model_config = Path(self.model_path) / 'config.json'
        weights = any((Path(self.model_path) / name).is_file() for name in ('model.safetensors', 'pytorch_model.bin'))
        processor_config = Path(self.model_path) / 'preprocessor_config.json'
        if not model_config.is_file() or not weights or not processor_config.is_file():
            return 'model_unavailable'
        try:
            if json.loads(model_config.read_text(encoding='utf-8')).get('model_type') != 'rt_detr':
                return 'model_unavailable'
        except (OSError, ValueError):
            return 'model_unavailable'
        return 'ready'

    def _load(self):
        if self.status != 'ready':
            raise RuntimeError(self.status)
        if self.model is not None:
            return
        with self._lock:
            if self.model is None:
                from transformers import RTDetrForObjectDetection, RTDetrImageProcessor
                self.processor = RTDetrImageProcessor.from_pretrained(self.model_path, local_files_only=True)
                self.model = RTDetrForObjectDetection.from_pretrained(self.model_path, local_files_only=True)
                self.model.eval()

    def detect_objects(self, image_path, confidence_threshold=None):
        from PIL import Image
        import torch

        threshold = settings.DETECTION_CONFIDENCE_THRESHOLD if confidence_threshold is None else confidence_threshold
        if not 0 <= threshold <= 1:
            raise ValueError('confidence_threshold must be between 0 and 1.')
        self._load()
        with Image.open(image_path) as source:
            image = source.convert('RGB')
        width, height = image.size
        inputs = self.processor(images=image, return_tensors='pt')
        with torch.inference_mode():
            outputs = self.model(**inputs)
        results = self.processor.post_process_object_detection(
            outputs, target_sizes=torch.tensor([[height, width]]), threshold=threshold,
        )[0]
        labels = self.model.config.id2label
        detections = []
        for score, label_id, box in zip(results['scores'], results['labels'], results['boxes']):
            x1, y1, x2, y2 = [float(value) for value in box.tolist()]
            x1, x2 = max(0.0, min(x1, width)), max(0.0, min(x2, width))
            y1, y2 = max(0.0, min(y1, height)), max(0.0, min(y2, height))
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append({
                'label': str(labels.get(int(label_id), int(label_id))),
                'confidence': float(score),
                'bbox': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2},
            })
        return detections

    @property
    def model_version(self):
        if self.model is None:
            return None
        return getattr(self.model.config, '_commit_hash', None) or getattr(self.model.config, 'transformers_version', None)


detection_service = DetectionService()
