import json
import hashlib
import os
from typing import Optional, List, Dict
from utils.logger import log

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, "users.json")

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _load_users() -> Dict:
    if not os.path.exists(USERS_FILE):
        return {"admin": {"hash": _hash("admin123"), "role": "admin"}}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error(f"Ошибка чтения {USERS_FILE}: {e}")
        return {"admin": {"hash": _hash("admin123"), "role": "admin"}}

def _save_users(users: Dict) -> bool:
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.error(f"Ошибка сохранения {USERS_FILE}: {e}")
        return False

def authenticate(username: str, password: str) -> Optional[str]:
    users = _load_users()
    if username in users:
        user_data = users[username]
        if isinstance(user_data, dict) and user_data["hash"] == _hash(password):
            log.info(f"Вход выполнен: {username}")
            return user_data["role"]
    log.warning(f"Неудачная попытка входа: {username}")
    return None

def add_user(username: str, password: str, role: str = "user") -> bool:
    users = _load_users()
    if username in users:
        log.warning(f"Пользователь {username} уже существует")
        return False
    users[username] = {"hash": _hash(password), "role": role}
    if _save_users(users):
        log.info(f"Пользователь добавлен: {username} ({role})")
        return True
    return False

def delete_user(username: str) -> bool:
    users = _load_users()
    if username not in users:
        log.warning(f"Пользователь {username} не найден")
        return False
    
    current_admins = sum(1 for u in users.values() if isinstance(u, dict) and u.get("role") == "admin")
    user_is_admin = username in users and isinstance(users[username], dict) and users[username].get("role") == "admin"
    
    if user_is_admin and current_admins <= 1:
        log.error(f"Нельзя удалить последнего администратора: {username}")
        return False
    
    try:
        del users[username]
        if _save_users(users):
            log.info(f"Пользователь удалён: {username}")
            return True
        return False
    except Exception as e:
        log.error(f"Ошибка при удалении пользователя {username}: {e}")
        return False

def list_users() -> List[Dict]:
    users = _load_users()
    return [
        {"username": name, "role": u["role"]} 
        for name, u in users.items() if isinstance(u, dict)
    ]

def get_user_count() -> int:
    return len(_load_users())

def promote_to_admin(username: str) -> bool:
    users = _load_users()
    if username not in users or username == "admin":
        return False
    if isinstance(users[username], dict):
        users[username]["role"] = "admin"
        return _save_users(users)
    return False