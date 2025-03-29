import sys
from pathlib import Path

def get_base_directory():
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
    return str(get_base_directory() / Path(*path_parts))