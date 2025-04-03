import os
import subprocess
import sys

from logging_config import logger, debug_logger


def run_script():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Используем относительный путь к скрипту
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_assistant.py")
    python_path = sys.executable

    # Проверяем, существует ли исполняемый файл Python
    if not os.path.exists(python_path):
        logger.info("Python не найден, проверьте установку.")
        debug_logger.info("Python не найден, проверьте установку.")
        sys.exit(1)

    # Запускаем скрипт
    try:
        subprocess.Popen([python_path, script_path], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        logger.error(f"Ошибка при запуске скрипта: {e}")
        debug_logger.error(f"Ошибка при запуске скрипта: {e}")


if __name__ == "__main__":
    run_script()
