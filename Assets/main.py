import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import log
from cli import show_main_menu, start_user_mode, login_user
from admin_cli import login_admin, admin_panel

def main():
    log.info("запуск программы")
    while True:
        choice = show_main_menu()
        if choice == '0':
            log.info("Завершение работы")
            break  
        elif choice == '1':
            if login_user():
                start_user_mode()
                break
            else:
                print("\nВозврат в меню...")
                continue
        elif choice == '2':
            if login_admin():
                admin_panel()
                print("\nПерезапустите систему для применения изменений")
            else:
                print("\nВозврат в меню...")
                continue
        else:
            print("Неверный ввод, попробуйте снова")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Работа прервана пользователем")
        print("\nОстановка...")
    except Exception as e:
        log.exception(f"Критическая ошибка: {e}")
        print(f"Ошибка: {e}")
        sys.exit(1)