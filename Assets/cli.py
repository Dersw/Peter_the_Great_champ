from utils.logger import log
from tts.synthesizer import TTSEngine
from stt.recognizer import STTEngine
from storage.auth_manager import authenticate
import config

def login_user() -> bool:
    print("\nАВТОРИЗАЦИЯ ПОЛЬЗОВАТЕЛЯ")
    username = input("Логин: ").strip()
    password = input("Пароль: ").strip()
    
    role = authenticate(username, password)
    if role == "user":
        log.info(f"Пользователь {username} авторизован")
        return True
    elif role == "admin":
        log.warning(f"Администратор {username} попытался войти в пользовательский режим")
        print("Администраторам доступен только режим администрирования")
        return False
    else:
        log.warning(f"Неудачная авторизация: {username}")
        print("Неверный логин или пароль")
        return False

def select_speaker() -> str:
    speakers = {
        "1": ("aidar", "aidar (Мужской)"),
        "2": ("baya", "baya (Женский)"),
        "3": ("kseniya", "kseniya (Женский, чёткий)"),
        "4": ("xenia", "xenia (Женский, мягкий)")
    }

    print("\n" + "=" * 45)
    print("ВЫБОР ГОЛОСА СИНТЕЗАТОРА")
    print("=" * 45)
    for key, (code, name) in speakers.items():
        print(f"  [{key}] {name}")
    print("=" * 45)

    while True:
        choice = input("Введите номер или название голоса: ").strip().lower()
        if choice in speakers:
            return speakers[choice][0]
        for code, name in speakers.values():
            if choice == code or choice in name.lower():
                return code
        print("Неверный ввод. Доступно: aidar, baya, kseniya, xenia\n")

def on_command_handler(command: str, tts: TTSEngine):
    log.info(f"Команда распознана: {command}")
    print(f"Команда: {command.lower()} | Озвучиваю...")
    phrase = config.TTS_PHRASES.get(command, "Команда принята.")
    tts.speak(phrase)

def start_user_mode():
    log.info("Запуск в режиме пользователя")
    
    config.TTS_SPEAKER = select_speaker()
    log.info(f"Голос синтезатора: {config.TTS_SPEAKER}")

    tts = TTSEngine()
    
    def on_command(command):
        on_command_handler(command, tts)

    stt = STTEngine(on_command)
    log.info("Ожидание команд...")
    stt.start()

def show_main_menu() -> str:
    print("=" * 50)
    print("1. Режим пользователя (голосовое управление)")
    print("2. Режим администратора (настройка)")
    print("0. Выход")
    print("=" * 50)
    return input("Выберите режим [1/2/0]: ").strip()