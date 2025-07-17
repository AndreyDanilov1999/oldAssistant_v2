import os
import re
from typing import Tuple, Optional, Dict
import requests
from logging_config import debug_logger
from path_builder import get_path


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


def check_all_versions() -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Получает все версии с сервера
    Возвращает кортеж: (стабильные_версии, экспериментальные_версии)
    """
    try:
        domain = "https://owl-app.ru"
        dev_domain = "http://127.0.0.1:5000"
        versions_url = f"{domain}/versions"

        response = requests.get(versions_url, timeout=5)
        response.raise_for_status()  # Генерирует исключение для HTTP-ошибок

        data = response.json()

        # Проверяем структуру ответа
        if not isinstance(data, dict):
            raise ValueError("Некорректный формат ответа сервера")

        # Получаем списки всех версий
        stable_versions = data.get("stable", [])
        experimental_versions = data.get("experimental", [])

        # Проверяем, что это действительно списки
        if not isinstance(stable_versions, list):
            stable_versions = []
        if not isinstance(experimental_versions, list):
            experimental_versions = []

        # Логируем информацию
        debug_logger.info(f"Получено стабильных версий: {len(stable_versions)}")
        debug_logger.info(f"Получено экспериментальных версий: {len(experimental_versions)}")

        return stable_versions, experimental_versions

    except requests.exceptions.RequestException as e:
        debug_logger.error(f"Ошибка соединения: {str(e)}")
        return None, None
    except ValueError as e:
        debug_logger.error(f"Ошибка формата данных: {str(e)}")
        return None, None
    except Exception as e:
        debug_logger.error(f"Неожиданная ошибка: {str(e)}")
        return None, None

def load_changelog():
    domain = "https://owl-app.ru"
    dev_domain = "http://127.0.0.1:5000"
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


def download_update(type_version, on_complete=None, version=None):
    """Загрузка файла с сохранением оригинального имени, очисткой старых версий и обработкой прерываний"""
    if type_version not in ["stable", "exp"]:
        debug_logger.error("Недопустимый тип версии")
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
        download_dir = get_path("update")
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
            debug_logger.info(f"Файл уже существует: {file_path}")
            if callable(on_complete):
                on_complete(file_path, success=True, skipped=True)
            return file_path

        # Удаляем старые временные файлы (если есть)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # Скачиваем во временный файл
        debug_logger.info(f"Начинаю загрузку: {filename}")
        with requests.get(download_url, stream=True, allow_redirects=True) as r:
            r.raise_for_status()

            # Получаем ожидаемый размер файла
            total_size = int(r.headers.get('content-length', 0))

            with open(temp_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # Фильтруем keep-alive chunks
                        f.write(chunk)

        # Проверяем целостность скачанного файла
        if os.path.getsize(temp_file_path) == total_size or total_size == 0:
            # Переименовываем временный файл в постоянный
            os.rename(temp_file_path, file_path)
            debug_logger.info(f"Файл успешно загружен: {file_path}")

            if callable(on_complete):
                on_complete(file_path, success=True, skipped=False)
            return file_path
        else:
            raise Exception("Размер скачанного файла не соответствует ожидаемому")

    except (requests.exceptions.RequestException, Exception) as e:
        error_msg = f"Ошибка при загрузке: {str(e)}"
        debug_logger.error(error_msg, exc_info=True)

        # Удаляем временный файл при ошибке
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                debug_logger.info(f"Удален неполный файл: {temp_file_path}")
            except Exception as cleanup_error:
                debug_logger.error(f"Ошибка при удалении временного файла: {str(cleanup_error)}")

        if callable(on_complete):
            on_complete(None, success=False, error=error_msg)
        return None


