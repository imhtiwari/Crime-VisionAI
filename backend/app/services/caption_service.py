import importlib.util
from pathlib import Path

from app.config import settings


class CaptionService:
    """Optional local BLIP caption adapter; model downloads are disabled."""

    def __init__(self):
        self.model_path = settings.CAPTION_MODEL_PATH.strip()
        self.model_name = Path(self.model_path).name if self.model_path else None
        self._processor = None
        self._model = None

    @property
    def status(self):
        if not self.model_path or not Path(self.model_path).is_dir():
            return 'model_not_configured'
        if not importlib.util.find_spec('torch') or not importlib.util.find_spec('transformers'):
            return 'model_unavailable'
        model_path = Path(self.model_path)
        if not (model_path / 'config.json').is_file() or not (model_path / 'preprocessor_config.json').is_file():
            return 'model_unavailable'
        if not any((model_path / name).is_file() for name in ('model.safetensors', 'pytorch_model.bin')):
            return 'model_unavailable'
        return 'ready'

    def caption(self, image_path):
        if self.status != 'ready':
            return {'status': self.status, 'text': None, 'model': self.model_name}
        from PIL import Image
        from transformers import BlipForConditionalGeneration, BlipProcessor
        import torch

        if self._model is None:
            self._processor = BlipProcessor.from_pretrained(self.model_path, local_files_only=True)
            self._model = BlipForConditionalGeneration.from_pretrained(self.model_path, local_files_only=True)
            self._model.eval()
        with Image.open(image_path) as source:
            inputs = self._processor(images=source.convert('RGB'), return_tensors='pt')
        with torch.inference_mode():
            output = self._model.generate(**inputs, max_new_tokens=80)
        text = self._processor.decode(output[0], skip_special_tokens=True)
        return {'status': 'completed', 'text': text, 'model': self.model_name}


caption_service = CaptionService()
