import os
import re
import requests
from logging_config import debug_logger
from path_builder import get_path


def check_version():
    try:
        domain = "https://owl-app.ru"
        dev_domain = "http://127.0.0.1:8000"
        version_url = f"{domain}/version"
        response = requests.get(version_url, timeout=5)  # Добавляем таймаут

        if response.status_code == 200:
            data = response.json()

            stable_data = data.get("stable", {}) or {}
            experimental_data = data.get("experimental", {}) or {}

            version = stable_data.get("version")
            exp_version = experimental_data.get("exp_version")

            if version:
                debug_logger.info(f"Последняя стабильная версия: {version}")
            if exp_version:
                debug_logger.info(f"Экспериментальная версия: {exp_version}")

            return version, exp_version
        else:
            debug_logger.error(f"Ошибка сервера: {response.status_code}")
            return None, None

    except requests.exceptions.RequestException as e:
        debug_logger.error(f"Ошибка соединения: {str(e)}")
        return None, None


def load_changelog():
    domain = "https://owl-app.ru"
    dev_domain = "http://127.0.0.1:8000"
    download_url = f"{domain}/getchangelog"
    changelog_path = get_path('update', 'changelog.md')

    try:
        # Создаем папку, если ее нет
        os.makedirs(os.path.dirname(changelog_path), exist_ok=True)

        with requests.get(download_url, stream=True) as response:
            response.raise_for_status()  # Проверяем статус ответа

            # Записываем содержимое в файл
            with open(changelog_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Пропускаем пустые chunk
                        f.write(chunk)

        debug_logger.debug(f"Changelog успешно сохранен в: {changelog_path}")
        return True

    except requests.exceptions.RequestException as e:
        debug_logger.error(f"Ошибка при загрузке changelog: {str(e)}")
        return False

def get_filename_from_cd(cd):
    """Получение имени файла из Content-Disposition"""
    if not cd:
        return None
    match = re.search(r'filename="?([^"]+)"?', cd)
    return match.group(1) if match else None

def download_update(type_version, on_complete=None):
    """Загрузка файла с сохранением оригинального имени и очисткой старых версий"""
    if type_version not in ["stable", "exp"]:
        debug_logger.error("Недопустимый тип версии")
        return None

    domain = "https://owl-app.ru"
    dev_domain = "http://127.0.0.1:8000"
    download_url = f"{domain}/download/{type_version}"

    try:
        download_dir = get_path("update")
        os.makedirs(download_dir, exist_ok=True)

        # Заголовок Content-Disposition и имя файла
        with requests.head(download_url, allow_redirects=True) as r:
            r.raise_for_status()
            content_disposition = r.headers.get('Content-Disposition')
            filename = get_filename_from_cd(content_disposition)

            if not filename:
                filename = f"{type_version}_update.zip"

        file_path = os.path.join(download_dir, filename)

        # Проверяем, существует ли такой файл уже
        if os.path.exists(file_path):
            debug_logger.info(f"Файл уже существует: {file_path}")
            if callable(on_complete):
                on_complete(file_path, success=True, skipped=True)
            return file_path

        # Скачиваем, только если файла нет
        debug_logger.info(f"Начинаю загрузку: {filename}")
        with requests.get(download_url, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        debug_logger.info(f"Файл успешно загружен: {file_path}")

        if callable(on_complete):
            on_complete(file_path, success=True, skipped=False)

        return file_path

    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка сети при загрузке: {str(e)}"
        debug_logger.error(error_msg)
        if callable(on_complete):
            on_complete(None, success=False, error=error_msg)
        return None
    except Exception as e:
        error_msg = f"Неожиданная ошибка: {str(e)}"
        debug_logger.error(error_msg, exc_info=True)
        if callable(on_complete):
            on_complete(None, success=False, error=error_msg)
        return None
