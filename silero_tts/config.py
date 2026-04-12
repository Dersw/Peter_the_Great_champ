from typing import Literal

MODELS = {
    "ru": {
        "model_speaker": "v5_4_ru",
        "lang_code": "ru",
        "speakers": ["aidar", "baya", "kseniya", "xenia"],
        "native_sr": 48000,
        "version": "v5",
    },
    "en": {
        "model_speaker": "v3_en",
        "lang_code": "en",
        "speakers": ["en_0"],
        "native_sr": 24000,
        "version": "v3",
    },
}

DEFAULT_SAMPLE_RATE = 48000
SILENCE_PADDING_SEC = 1
DEFAULT_VOLUME = 0.8
DEFAULT_SPEED = 1.0

VOLUME_RANGE = (0.1, 2.0)
SPEED_RANGE = (0.5, 2.0)

DeviceType = Literal["cpu", "cuda", "mps", "auto"]