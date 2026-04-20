import os
import sys
from utils.logger import log
from storage.data_manager import load_custom

SAMPLE_RATE = 16000
COMMAND_TIMEOUT = 0.8
ENERGY_THRESHOLD = 300
DEBOUNCE_INTERVAL = 1.5

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model")

BASE_COMMANDS = {
    "стоп": "СТОП", "пуск": "ПУСК", "запуск": "ПУСК",
    "дальше": "ДАЛЬШЕ", "далее": "ДАЛЬШЕ", "тревога": "ТРЕВОГА"
}

BASE_PHRASES = {
    "ПУСК": "Пуск разрешён.",
    "СТОП": "Остановка выполнена.",
    "ДАЛЬШЕ": "Продолжаем работу.",
    "ТРЕВОГА": "Объявлена тревога в цеху."
}

custom = load_custom()
COMMANDS = {**BASE_COMMANDS, **custom.get("commands", {})}
TTS_PHRASES = {**BASE_PHRASES, **custom.get("phrases", {})}

log.info(f"Загружено команд: {len(COMMANDS)} (базовых: {len(BASE_COMMANDS)}, кастомных: {len(custom.get('commands', {}))})")

TTS_SPEAKER = None