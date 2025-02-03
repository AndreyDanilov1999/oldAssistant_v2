import logging
import os
import sys

# Определяем базовый путь
if getattr(sys, 'frozen', False):
    # Если скрипт запущен как исполняемый файл
    current_dir = os.path.dirname(sys.executable)
    # Определяем путь к папке _internal
    internal_dir = os.path.join(current_dir, '_internal')
    # Создаем папку _internal, если она не существует
    os.makedirs(internal_dir, exist_ok=True)
else:
    # Если скрипт запущен как обычный скрипт
    current_dir = os.path.dirname(__file__)
    # Используем текущую директорию для логов
    internal_dir = current_dir

# Определяем путь к файлу логов
log_file_path = os.path.join(internal_dir, 'assistant.log')

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования (INFO, DEBUG, ERROR и т.д.)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Формат сообщений
    filename=log_file_path,  # Используйте полный путь к файлу для записи логов
    filemode="a",  # Режим записи (добавление в конец файла)
    encoding="utf-8",
)

logger = logging.getLogger("assistant")