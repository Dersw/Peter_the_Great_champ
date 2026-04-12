import torch
import scipy
import numpy as np
from typing import Optional, Literal
from loguru import logger

from .config import DeviceType


def resolve_device(requested: Optional[DeviceType]) -> torch.device:
    """Определяет устройство для инференса."""
    if requested in (None, "auto"):
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(requested)


def warmup_model(tts_instance) -> None:
    """Прогревает модель для ускорения первого запроса."""
    try:
        txt = "warmup" if tts_instance.current_lang != "ru" else "прогрев"
        with torch.inference_mode():
            tts_instance.synthesize(txt, put_accent=False, put_yo=False)
        logger.info(" Model warmed up.")
    except:
        pass 


def adjust_speed(audio_np: np.ndarray, speed: float) -> np.ndarray:
    """Изменяет скорость воспроизведения (ресемплинг)."""
    if speed == 1.0:
        return audio_np
    from scipy.signal import resample
    new_len = int(len(audio_np) / speed)
    return resample(audio_np, new_len)