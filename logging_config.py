import logging
import os
import sys
from logging.handlers import RotatingFileHandler

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
if not os.path.exists(os.path.join(internal_dir, "log")):
    os.makedirs(os.path.join(internal_dir, "log"))
debug_file_path = os.path.join(internal_dir, "log", "debug_assist.log")

logger = logging.getLogger("assistant")
logger.setLevel(logging.INFO)  # Уровень логирования (INFO, DEBUG, ERROR и т.д.)
handler = RotatingFileHandler(
    log_file_path,
    maxBytes=5 * 1024 * 1024,  # Максимальный размер файла (5 МБ)
    backupCount=5,  # Количество резервных файлов
    encoding='utf-8'
)
formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

debug_logger = logging.getLogger("debug_assist")
debug_logger.setLevel(logging.DEBUG)
debug_handler = RotatingFileHandler(
    debug_file_path,
    maxBytes=5 * 1024 * 1024,  # Максимальный размер файла (5 МБ)
    backupCount=5,  # Количество резервных файлов
    encoding='utf-8'
)
debug_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
debug_handler.setFormatter(debug_formatter)
debug_logger.addHandler(debug_handler)
