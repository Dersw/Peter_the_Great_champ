import json
import os
from typing import Dict
from utils.logger import log

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
CUSTOM_FILE = os.path.join(DATA_DIR, "custom_commands.json")

def load_custom() -> Dict:
    if not os.path.exists(CUSTOM_FILE):
        return {"commands": {}, "phrases": {}}
    try:
        with open(CUSTOM_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error(f"Ошибка чтения {CUSTOM_FILE}: {e}")
        return {"commands": {}, "phrases": {}}

def save_custom(data: Dict) -> bool:
    try:
        with open(CUSTOM_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info("Кастомная команда сохранена")
        return True
    except Exception as e:
        log.error(f"Ошибка сохранения {CUSTOM_FILE}: {e}")
        return False

def add_command(keyword: str, code: str, phrase: str) -> bool:
    data = load_custom()
    data["commands"][keyword.lower()] = code.upper()
    data["phrases"][code.upper()] = phrase
    return save_custom(data)

def list_custom_commands() -> Dict:
    return load_custom().get("commands", {})