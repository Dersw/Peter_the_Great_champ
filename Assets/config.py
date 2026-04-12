import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(PROJECT_DIR, "model")

SAMPLE_RATE = 16000
COMMAND_TIMEOUT = 0.8
ENERGY_THRESHOLD = 300
DEBOUNCE_INTERVAL = 1.5

COMMANDS = {
    "стоп": "СТОП", "пуск": "ПУСК", "запуск": "ПУСК",
    "дальше": "ДАЛЬШЕ", "далее": "ДАЛЬШЕ", "тревога": "ТРЕВОГА"
}

TTS_PHRASES = {
    "ПУСК": "Пуск разрешён.",
    "СТОП": "Остановка выполнена.",
    "ДАЛЬШЕ": "Продолжаем работу.",
    "ТРЕВОГА": "Объявлена тревога в цеху."
}

TTS_SPEAKER = None