import threading
import torch
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import Optional
from loguru import logger
from .config import MODELS, DeviceType
from .utils import resolve_device, warmup_model
from .audio import add_padding


class OfflineSileroTTS:
    def __init__(
        self,
        languages: list[str] = ["ru"],
        device: Optional[DeviceType] = None,
        cache_dir: Optional[str] = None,
        optimize: bool = True,
    ) -> None:
        for lang in languages:
            if lang not in MODELS:
                raise ValueError(f"Unsupported language: {lang}")

        self.languages = languages
        self.current_lang = languages[0]
        self.device = resolve_device(device)
        self._lock = threading.Lock()
        self.models: dict[str, any] = {}

        if optimize:
            try:
                torch.set_float32_matmul_precision("high")
            except AttributeError:
                pass
            torch.set_num_threads(4)

        for lang in languages:
            self.models[lang] = self._load_model(lang, cache_dir)

        logger.info(f"Silero TTS initialized. Languages: {languages} | Device: {self.device}")
        warmup_model(self)

    def _load_model(self, lang_key: str, cache_dir: Optional[str]):
        cfg = MODELS[lang_key]
        logger.info(f"Loading {lang_key} model...")
        try:
            res = torch.hub.load(
                "snakers4/silero-models", "silero_tts",
                language=cfg["lang_code"], speaker=cfg["model_speaker"],
                trust_repo=True, cache=cache_dir
            )
            model = res[0] if isinstance(res, (tuple, list)) else res
            model.to(self.device)
            if hasattr(model, "eval"):
                model.eval()
            logger.info(f"{lang_key} model loaded.")
            return model
        except Exception as e:
            logger.critical(f"Failed to load {lang_key}: {e}")
            raise RuntimeError(f"Не удалось загрузить модель {lang_key}.") from e

    def synthesize(
        self,
        text: str,
        speaker: Optional[str] = None,
        put_accent: bool = True,
        put_yo: bool = False,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        if not text.strip():
            raise ValueError("Текст не может быть пустым.")

        cfg = MODELS[self.current_lang]
        speaker = speaker or cfg["speakers"][0]
        if speaker not in cfg["speakers"]:
            raise ValueError(f"Speaker '{speaker}' not in {cfg['speakers']}")

        native_sr = cfg["native_sr"]
        model = self.models[self.current_lang]
        is_v3 = cfg["version"] == "v3"

        with self._lock:
            with torch.inference_mode():
                if not is_v3:
                    audio_tensor = model.apply_tts(
                        text=text, speaker=speaker, sample_rate=native_sr,
                        put_accent=put_accent, put_yo=put_yo
                    )
                else:
                    audio_tensor = model.apply_tts(
                        text=text, speaker=speaker, sample_rate=native_sr
                    )

        if isinstance(audio_tensor, (list, tuple)):
            audio_tensor = audio_tensor[0]
        audio_np = audio_tensor.squeeze().cpu().numpy()
        audio_np = add_padding(audio_np, native_sr)

        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(p), audio_np, native_sr)
            logger.info(f"Audio saved: {p}")
        return audio_np

    def switch_language(self, lang_key: str) -> None:
        if lang_key not in MODELS:
            raise ValueError(f"Language '{lang_key}' not supported.")
        if lang_key not in self.models:
            self.models[lang_key] = self._load_model(lang_key, cache_dir=None)
        self.current_lang = lang_key
        logger.info(f" Язык переключён на: {lang_key}")

    def save_to_file(
        self, text: str, output_path: str, speaker: Optional[str] = None, **kwargs
    ) -> Path:
        self.synthesize(text, speaker, output_path=output_path, **kwargs)
        return Path(output_path)