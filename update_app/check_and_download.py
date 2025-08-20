import os
import re
import requests
from PyQt5.QtCore import QThread, pyqtSignal

from utils import logger, get_base_directory


class VersionCheckThread(QThread):
    version_checked = pyqtSignal(str, str)  # Сигнал для stable и exp версий
    check_failed = pyqtSignal()  # Сигнал при ошибке

    def run(self):
        try:
            domain = "https://owl-app.ru"
            dev_domain = "http://127.0.0.1:5000"
            version_url = f"{domain}/version"
            response = requests.get(version_url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                stable = data.get("stable", {}).get("version", "")
                exp = data.get("experimental", {}).get("exp_version", "")
                if stable:
                    logger.info(f"Последняя стабильная версия: {stable}")

                if exp:
                    logger.info(f"Экспериментальная версия: {exp}")
                self.version_checked.emit(stable, exp)
            else:
                self.check_failed.emit()
        except requests.exceptions.RequestException:
            self.check_failed.emit()

def check_version():
    try:
        domain = "https://owl-app.ru"
        dev_domain = "http://127.0.0.1:5000"
        version_url = f"{domain}/version"
        response = requests.get(version_url, timeout=5)  # Добавляем таймаут

        if response.status_code == 200:
            data = response.json()

            stable_data = data.get("stable", {}) or {}
            experimental_data = data.get("experimental", {}) or {}

            version = stable_data.get("version")
            exp_version = experimental_data.get("exp_version")

            if version:
                logger.info(f"Последняя стабильная версия: {version}")
            if exp_version:
                logger.info(f"Экспериментальная версия: {exp_version}")

            return version, exp_version
        else:
            logger.error(f"Ошибка сервера: {response.status_code}")
            return None, None

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка соединения: {str(e)}")
        return None, None


class DownloadThread(QThread):
    download_complete = pyqtSignal(str, bool, bool, str)  # file_path, success, skipped, error
    download_progress = pyqtSignal(int)

    def __init__(self, type_version, version=None, parent=None):
        super().__init__(parent)
        self.type_version = type_version
        self.version = version

    def run(self):
        download_update(
            type_version=self.type_version,
            on_complete=self._handle_complete,
            on_progress=self._handle_progress,
            version=self.version)

    def _handle_complete(self, file_path, success=True, skipped=False, error=None):
        self.download_complete.emit(file_path, success, skipped, error)

    def _handle_progress(self, progress_percent):
        self.download_progress.emit(progress_percent)

def get_filename_from_cd(cd):
    """Получение имени файла из Content-Disposition"""
    if not cd:
        return None
    match = re.search(r'filename="?([^"]+)"?', cd)
    return match.group(1) if match else None


def download_update(type_version, on_complete=None, on_progress=None, version=None):
    """Загрузка файла с сохранением оригинального имени, очисткой старых версий и обработкой прерываний"""
    if type_version not in ["stable", "exp"]:
        logger.error("Недопустимый тип версии")
        return None

    domain = "https://owl-app.ru"
    dev_domain = "http://127.0.0.1:5000"
    download_url = None
    temp_suffix = ".tempdownload"  # Суффикс для временных файлов
    file_path = None
    temp_file_path = None

    if version is None:
        download_url = f"{domain}/download/{type_version}"
    else:
        download_url = f"{domain}/load/{type_version}/{version}"

    try:
        root_dir = get_base_directory()
        download_dir = root_dir / "update"
        os.makedirs(download_dir, exist_ok=True)

        # Получаем имя файла из заголовков
        with requests.head(download_url, allow_redirects=True) as r:
            r.raise_for_status()
            content_disposition = r.headers.get('Content-Disposition')
            filename = get_filename_from_cd(content_disposition) or f"{type_version}_update.zip"

        file_path = os.path.join(download_dir, filename)
        temp_file_path = file_path + temp_suffix

        # Если уже есть полная версия файла
        if os.path.exists(file_path):
            logger.info(f"Файл уже существует: {file_path}")
            if callable(on_complete):
                on_complete(file_path, success=True, skipped=True)
            return file_path

        # Удаляем старые временные файлы (если есть)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # Скачиваем во временный файл
        logger.info(f"Начинаю загрузку: {filename}")
        with requests.get(download_url, stream=True, allow_redirects=True) as r:
            r.raise_for_status()

            # Получаем ожидаемый размер файла
            total_size = int(r.headers.get('content-length', 0))
            downloaded_size = 0

            with open(temp_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # Фильтруем keep-alive chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Отправляем прогресс (от 0 до 100%)
                        if total_size > 0 and callable(on_progress):
                            progress_percent = int((downloaded_size / total_size) * 100)
                            on_progress(progress_percent)

        # Проверяем целостность скачанного файла
        if os.path.getsize(temp_file_path) == total_size or total_size == 0:
            # Переименовываем временный файл в постоянный
            os.rename(temp_file_path, file_path)
            logger.info(f"Файл успешно загружен: {file_path}")

            if callable(on_complete):
                on_complete(file_path, success=True, skipped=False)
            return file_path
        else:
            raise Exception("Размер скачанного файла не соответствует ожидаемому")

    except (requests.exceptions.RequestException, Exception) as e:
        error_msg = f"Ошибка при загрузке: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Удаляем временный файл при ошибке
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Удален неполный файл: {temp_file_path}")
            except Exception as cleanup_error:
                logger.error(f"Ошибка при удалении временного файла: {str(cleanup_error)}")

        if callable(on_complete):
            on_complete(None, success=False, error=error_msg)
        return None