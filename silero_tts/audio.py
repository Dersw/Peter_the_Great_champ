"""Работа с аудио: воспроизведение, конвертация, пост-обработка."""

import os
import sys
import time
import threading
import tempfile
import soundfile as sf
import numpy as np
from loguru import logger

from .config import DEFAULT_SAMPLE_RATE, SILENCE_PADDING_SEC


def add_padding(audio: np.ndarray, sample_rate: int, seconds: float = SILENCE_PADDING_SEC) -> np.ndarray:
    """Добавляет тишину в конец аудио для плавного завершения."""
    padding_samples = int(sample_rate * seconds)
    return np.concatenate([audio, np.zeros(padding_samples, dtype=audio.dtype)])


def convert_to_int16(audio: np.ndarray, volume: float = 1.0) -> np.ndarray:
    """Конвертирует аудио в 16-bit PCM с учётом громкости."""
    if audio.dtype != np.int16:
        return np.clip(audio * 32768 * volume, -32768, 32767).astype(np.int16)
    return audio


def play_audio(audio_np: np.ndarray, sample_rate: int, volume: float = 1.0) -> None:
    """🔇 Фоновое воспроизведение БЕЗ открытия окон."""
    duration = len(audio_np) / sample_rate if len(audio_np) > 0 else 0.5
    audio_int16 = convert_to_int16(audio_np, volume)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        sf.write(tmp_path, audio_int16, sample_rate)

        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(tmp_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        elif sys.platform == "darwin":
            os.system(f"afplay '{tmp_path}' &")
        else:
            os.system(f"aplay '{tmp_path}' &")

        # Фоновая очистка файла
        threading.Thread(target=_cleanup_temp, args=(tmp_path, duration + 1.0), daemon=True).start()
    except Exception as e:
        logger.error(f"Playback failed: {e}")
        try:
            os.unlink(tmp_path)
        except:
            pass


def _cleanup_temp(path: str, delay: float):
    """Удаляет временный файл с задержкой."""
    time.sleep(delay)
    try:
        if os.path.exists(path):
            os.unlink(path)
    except:
        pass