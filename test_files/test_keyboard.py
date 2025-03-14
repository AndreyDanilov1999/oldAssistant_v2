import os
import zipfile
import shutil
import subprocess
import sys
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog

# Путь к текущей версии программы
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
USER_SETTINGS_DIR = os.path.join(CURRENT_DIR, "user_settings")

class UpdateApp(QDialog):

# Функция для создания задачи в планировщике
def create_scheduler_task(archive_path):
    # Команда для выполнения обновления
    update_script = f"""
    @echo off
    timeout /t 5 /nobreak >nul
    taskkill /im Assistant.exe /f
    {"powershell -Command Expand-Archive -Path '" + archive_path + "' -DestinationPath '" + CURRENT_DIR.replace(os.sep, '/') + "' -Force" if archive_path.endswith('.zip') else f'"{os.path.join(CURRENT_DIR, "unrar.exe")}" x "{archive_path}" "{CURRENT_DIR.replace(os.sep, "/")}"'}
    xcopy "{os.path.join(CURRENT_DIR, "user_settings").replace(os.sep, "/")}" "{os.path.join(CURRENT_DIR, "new_version", "user_settings").replace(os.sep, "/")}" /E /I /Y
    start "" "{os.path.join(CURRENT_DIR, "new_version", "Assistant.exe").replace(os.sep, "/")}"
    """

    # Сохраняем команду в bat-файл
    with open("update.bat", "w") as f:
        f.write(update_script)

    # Создаем задачу в планировщике
    subprocess.run([
        "schtasks", "/create", "/tn", "AssistantUpdate", "/tr",
        f'"{os.path.abspath("update.bat")}"', "/sc", "once", "/st", "00:00", "/f"
    ])


# Функция для выбора архива
def select_archive():
    app = QApplication(sys.argv)
    archive_path, _ = QFileDialog.getOpenFileName(
        None,
        "Выберите архив с новой версией",
        "",
        "ZIP files (*.zip);;RAR files (*.rar)"
    )
    return archive_path


# Основная функция
def main():
    # Выбираем архив
    archive_path = select_archive()
    if not archive_path:
        QMessageBox.warning(None, "Ошибка", "Архив не выбран.")
        return

    # Создаем задачу в планировщике
    create_scheduler_task(archive_path)
    QMessageBox.information(None, "Успех", "Задача в планировщике создана. Закройте программу для обновления.")


if __name__ == "__main__":
    main()