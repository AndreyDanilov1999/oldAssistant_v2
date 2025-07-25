"""
Модуль для замены файла Update.exe на новый
"""
import logging
import os
import shutil
import sys
from pathlib import Path

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

logger = logging.getLogger("replace_update")
logger.setLevel(logging.DEBUG)  # Уровень логирования

# Формат сообщений
formatter = logging.Formatter(
    fmt="[{levelname}] {asctime} | {message}",
    datefmt="%H:%M:%S",
    style="{"
)
root = get_base_directory()
log_path = os.path.join(root, "user_settings", "replace_updater.log")

file_handler = logging.FileHandler(log_path, encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Добавляем обработчик к логгеру (если его ещё нет)
if not logger.handlers:
    logger.addHandler(file_handler)


def main():
    root_dir = get_base_directory()  # Корень (Assistant/)
    update_pack_dir = root_dir / "update_pack"
    new_updater = os.path.join(update_pack_dir, "_internal", "Update.exe")
    old_updater = os.path.join(root_dir, "Update.exe")
    logger.info(f"old_file:{old_updater},\n new_file:{new_updater}")

    # Проверяем, существует ли новый файл
    if not os.path.exists(new_updater):
        logger.info("❌ Новый Update.exe не найден в update_pack")
        return

    # Удаляем старый (если существует)
    if os.path.exists(old_updater):
        try:
            os.remove(old_updater)
            logger.info("✅ Старый Update.exe удалён")
        except Exception as e:
            logger.error(f"❌ Не удалось удалить старый Update.exe: {e}")
            return

    # Копируем новый
    try:
        shutil.copy2(new_updater, old_updater)
        logger.info("✅ Update.exe успешно обновлён")
    except Exception as e:
        logger.error(f"❌ Ошибка копирования: {e}")

if __name__ == "__main__":
    main()