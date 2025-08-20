import configparser
import logging
import sys
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger("update")
logger.setLevel(logging.DEBUG)  # Уровень логирования

# Формат сообщений
formatter = logging.Formatter(
    fmt="[{levelname}] {asctime} | {message}",
    style="{"
)

# Обработчик: вывод в консоль
file_handler = logging.FileHandler("update.log", encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Добавляем обработчик к логгеру (если его ещё нет)
if not logger.handlers:
    logger.addHandler(file_handler)

def get_directory():
    """Автоматически определяет корневую директорию для всех режимов"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS  # onefile режим
        base = Path(sys.executable).parent
        internal = base / '_internal'
        return internal if internal.exists() else base
    return Path(__file__).parent  # режим разработки (корень проекта)

def get_path(*path_parts):
    """Строит абсолютный путь, идентичный в обоих режимах"""
    return str(get_directory() / Path(*path_parts))

def get_resource_path(relative_path):
    """Универсальный путь для ресурсов внутри/снаружи EXE"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            # Режим onefile: ресурсы во временной папке _MEIPASS
            base_path = Path(sys._MEIPASS)
        else:
            # Режим onedir: ресурсы в папке с EXE
            base_path = Path(sys.executable).parent
    else:
        # Режим разработки
        base_path = Path(__file__).parent

    return base_path / relative_path

def get_base_directory():
    """Возвращает правильный базовый путь в любом режиме"""
    if getattr(sys, 'frozen', False):
        # Режим exe (onefile или onedir)
        if hasattr(sys, '_MEIPASS'):
            # onefile режим - возвращаем папку с exe, а не временную
            return Path(sys.executable).parent
        # onedir режим
        return Path(sys.executable).parent
    # Режим разработки
    return Path(__file__).parent

def get_config_value(section, key, default=None):
    """Получение конкретного значения из конфига"""
    config = configparser.ConfigParser()
    root = get_base_directory()
    config_path = root / "config.ini"
    config.read(config_path, encoding='utf-8')
    return config.get(section, key, fallback=default)

class UpdateStatusSignal(QObject):
    status_update = pyqtSignal(str, int)

update_signal = UpdateStatusSignal()

class RunAppSignal(QObject):
    run_main_app = pyqtSignal()

run_app_signal = RunAppSignal()