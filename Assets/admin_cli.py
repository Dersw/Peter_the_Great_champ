from storage.data_manager import add_command, list_custom_commands, save_custom
from storage.auth_manager import authenticate, add_user, delete_user, list_users, promote_to_admin
from utils.logger import log

def login_admin() -> bool:
    print("\nАВТОРИЗАЦИЯ АДМИНИСТРАТОРА")
    username = input("Логин: ").strip()
    password = input("Пароль: ").strip()
    
    role = authenticate(username, password)
    if role == "admin":
        log.info(f"Администратор {username} авторизован")
        return True
    else:
        log.warning(f"Ошибка авторизации: {username}")
        print("Неверный логин или пароль")
        return False

def admin_panel():
    log.info("Запуск панели администратора")
    
    while True:
        print("\nПАНЕЛЬ АДМИНИСТРАТОРА")
        print("1. Добавить команду")
        print("2. Показать кастомные команды")
        print("3. Добавить пользователя")
        print("4. Удалить пользователя")
        print("5. Список пользователей")
        print("6. Сбросить кастомные команды")
        print("7. Повысить пользователя до админа")
        print("0. Выход")
        print("=" * 50)
        
        choice = input("Выбор > ").strip()
        
        if choice == '1':
            _add_command_flow()
        elif choice == '2':
            _list_commands_flow()
        elif choice == '3':
            _add_user_flow()
        elif choice == '4':
            _delete_user_flow()
        elif choice == '5':
            _list_users_flow()
        elif choice == '6':
            _reset_custom_flow()
        elif choice == '7':
            _promote_user_flow()
        elif choice == '0':
            log.info("Выход из панели администратора")
            break
        else:
            print("Неверный ввод")

def _add_command_flow():
    keyword = input("Триггер: ").strip().lower()
    code = input("Код команды: ").strip().upper()
    phrase = input("Фраза для озвучки: ").strip()
    if keyword and code and phrase:
        if add_command(keyword, code, phrase):
            print("Команда добавлена!")
        else:
            print("Ошибка сохранения")
    else:
        print("Заполните все поля")

def _list_commands_flow():
    cmds = list_custom_commands()
    print("\nКастомные команды:")
    if cmds:
        for k, v in cmds.items():
            print(f"  '{k}' -> {v}")
    else:
        print("  (пусто)")

def _add_user_flow():
    username = input("Логин: ").strip()
    password = input("Пароль: ").strip()
    role = input("Роль (user/admin) [по умолчанию user]: ").strip().lower() or "user"
    
    if role not in ("user", "admin"):
        print("Неверная роль. Доступно: user, admin")
        return
        
    if username and password:
        if add_user(username, password, role):
            print(f"Пользователь добавлен с ролью: {role}")
        else:
            print("Пользователь уже существует")

def _delete_user_flow():
    print("\nТекущие пользователи:")
    users = list_users()
    for i, u in enumerate(users, 1):
        marker = "[ADMIN]" if u["role"] == "admin" else "[USER]"
        print(f"  {i}. {marker} {u['username']}")
    
    target = input("\nВведите имя для удаления: ").strip()
    if not target:
        return
    if delete_user(target):
        print(f"Пользователь '{target}' удалён")
    else:
        print(f"Не удалось удалить '{target}'")

def _list_users_flow():
    print("\nПользователи:")
    users = list_users()
    for u in users:
        marker = "[ADMIN]" if u["role"] == "admin" else "[USER]"
        print(f"  {marker} {u['username']}")

def _reset_custom_flow():
    confirm = input("Удалить ВСЕ кастомные команды? (Y/n): ").strip().lower()
    if confirm == "y" or confirm == "д":
        if save_custom({"commands": {}, "phrases": {}}):
            print("Кастомные команды сброшены")

def _promote_user_flow():
    print("\nДоступные пользователи для повышения:")
    users = list_users()
    candidates = [u for u in users if u["role"] == "user"]
    
    if not candidates:
        print("Нет обычных пользователей для повышения")
        return
        
    for i, u in enumerate(candidates, 1):
        print(f"  {i}. {u['username']}")
    
    choice = input("Введите номер или имя пользователя: ").strip()
    
    target = None
    if choice.isdigit() and 1 <= int(choice) <= len(candidates):
        target = candidates[int(choice) - 1]["username"]
    else:
        for u in candidates:
            if u["username"] == choice:
                target = choice
                break
    
    if target and promote_to_admin(target):
        print(f"Пользователь '{target}' повышен до администратора")
    else:
        print("Не удалось повысить пользователя")