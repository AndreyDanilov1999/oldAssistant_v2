"""
Функции для запуска и закрытия программ и игр
"""
import json
import os
import subprocess
import sys
import time
import psutil
import pygetwindow as gw
from win32com.client import Dispatch
from lists import get_audio_paths
from logging_config import logger
from speak_functions import react, react_detail


def get_base_directory():
    """
    Возвращает базовую директорию для файлов в зависимости от режима выполнения.
    - Если программа запущена как исполняемый файл, возвращает директорию исполняемого файла.
    - Если программа запущена как скрипт, возвращает директорию скрипта.
    """
    if getattr(sys, 'frozen', False):
        # Если программа запущена как исполняемый файл
        if hasattr(sys, '_MEIPASS'):
            # Если ресурсы упакованы в исполняемый файл (один файл)
            base_path = sys._MEIPASS
        else:
            # Если ресурсы находятся рядом с исполняемым файлом (папка dist)
            base_path = os.path.dirname(sys.executable)
    else:
        # Если программа запущена как скрипт
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path


def load_settings(settings_file):
    """Загрузка настроек из файла"""
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings  # Возвращаем все настройки
        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл {settings_file} содержит некорректный JSON.")
    else:
        logger.error(f"Файл настроек {settings_file} не найден.")

    return {}  # Возвращаем пустой словарь, если файл не найден или ошибка


def get_current_speaker(settings_file):
    """
    Получение текущего спикера
    :param settings_file:
    :return:
    """
    settings = load_settings(settings_file)
    return settings.get("voice", "rogue")  # Возвращаем голос или значение по умолчанию


def get_steam_path(settings_file):
    """
    Получение текущего пути к исполняемому файлу Steam
    :param settings_file:
    :return:
    """
    settings = load_settings(settings_file)
    return settings.get("steam_path", "")  # Возвращаем путь к стим или пустую строку, если не нашлось


def get_target_path(shortcut_path):
    """Извлекает путь к исполняемому файлу и аргументы из ярлыка."""
    try:
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        return shortcut.Targetpath, shortcut.Arguments
    except Exception as e:
        logger.error(f"Ошибка при извлечении пути из ярлыка {shortcut_path}: {e}")
        return None, None


def fix_path(path):
    """Заменяет обратные слэши на прямые в пути."""
    return path.replace("\\", "/")


def get_process_name(target_path):
    """Извлекает имя процесса из пути к исполняемому файлу."""
    if target_path is None:
        return None
    return os.path.basename(target_path)


def read_url_shortcut(url_path):
    """Читает .url файл и извлекает game_id или URL."""
    try:
        with open(url_path, 'r', encoding='utf-8') as file:
            content = file.read()

        for line in content.splitlines():
            if line.startswith('URL='):
                url = line[4:]  # Извлекаем значение после "URL="
                # Если это Steam-ссылка, извлекаем game_id
                if url.startswith("steam://rungameid/"):
                    return url[18:]  # Возвращаем game_id
                # Если это Epic Games-ссылка, возвращаем полный URL
                elif url.startswith("com.epicgames.launcher://"):
                    return url
                # Иначе возвращаем как есть (на случай других типов ссылок)
                return url
        return None
    except Exception as e:
        raise Exception(f"Ошибка при чтении файла .url: {e}")


def get_all_processes():
    """Возвращает список всех текущих процессов."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        processes.append(proc.info['name'])
    return processes


def find_new_processes(before_processes, after_processes):
    """Находит все новые процессы, которые появились после запуска программы."""
    before_set = set(before_processes)
    after_set = set(after_processes)
    new_processes = after_set - before_set  # Находим разницу
    return list(new_processes)  # Возвращаем все новые процессы


def save_process_names(shortcut_name, process_names):
    """Сохраняет имена процессов в файл, обновляя данные, если они уже существуют."""
    try:
        new_data = {shortcut_name: process_names}
        process_names_file = os.path.join(get_base_directory(), 'user_settings',
                                          'process_names.json')  # Полный путь к файлу

        if os.path.exists(process_names_file):
            with open(process_names_file, 'r', encoding='utf-8') as file:
                try:
                    existing_data = json.load(file)  # Читаем весь JSON
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []

        found = False
        for entry in existing_data:
            if shortcut_name in entry:
                entry[shortcut_name] = process_names
                found = True
                break

        if not found:
            existing_data.append(new_data)

        with open(process_names_file, 'w', encoding='utf-8') as file:
            json.dump(existing_data, file, indent=4, ensure_ascii=False)
            file.write('\n')

        logger.info(f"Имена процессов для ярлыка '{shortcut_name}' сохранены в файл.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении имен процессов: {e}")


def get_process_names_from_file(shortcut_name):
    """Возвращает список имен процессов для указанного ярлыка из файла."""
    try:
        process_names = []
        process_names_file = os.path.join(get_base_directory(), 'user_settings',
                                          'process_names.json')  # Полный путь к файлу

        if os.path.exists(process_names_file):
            with open(process_names_file, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                    for entry in data:
                        if shortcut_name in entry:
                            process_names = entry[shortcut_name]
                            break
                except json.JSONDecodeError:
                    logger.error("Ошибка: файл содержит некорректный JSON.")
        return process_names
    except Exception as e:
        logger.error(f"Ошибка при чтении имен процессов: {e}")
        return []


def close_program(process_name):
    """Завершает все процессы с указанным именем."""
    try:
        subprocess.run(['taskkill', '/IM', process_name, '/F'], check=True)
        logger.info(f"Все процессы {process_name} успешно завершены.")
    except subprocess.CalledProcessError:
        logger.error(f"Не удалось завершить процесс {process_name}.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")


def search_links():
    """
    Поиск ярлыков по ключевой папке
    Получение и сохранение имени ярлыков в json
    """
    root_folder = os.path.join(get_base_directory(), 'user_settings',
                               "links for assist")  # Полный путь к папке с ярлыками
    root_links = os.path.join(get_base_directory(), 'user_settings', "links.json")

    # Очистка файла links.json перед началом поиска
    with open(root_links, 'w', encoding='utf-8') as file:
        file.write('{}')  # Записываем пустой JSON объект

    # Поиск новых ярлыков в директории
    current_shortcuts = {}
    for filename in os.listdir(root_folder):
        if filename.endswith(".lnk") or filename.endswith(".url"):
            # Формируем полный путь к ярлыку
            shortcut_path = os.path.join(root_folder, filename)
            current_shortcuts[filename] = shortcut_path

    # Сохраняем команды в JSON-файл
    with open(root_links, 'w', encoding='utf-8') as file:
        json.dump(current_shortcuts, file, ensure_ascii=False, indent=4)
        logger.info("Ярлыки сохранены в файле: %s", root_links)


def handler_links(filename, action):
    """
    Обработчик ярлыков в зависимости от их расширения
    """
    global game_id, target_path, process_name, game_id_or_url, args_list
    root_folder = os.path.join(get_base_directory(), 'user_settings', "links for assist")
    # Получаем путь к ярлыку
    shortcut_path = os.path.join(root_folder, filename)

    # Обработка .lnk файлов
    if filename.endswith(".lnk"):
        try:
            target_path, arguments = get_target_path(shortcut_path)
            args_list = arguments.split()
            # Исправляем пути
            target_path = fix_path(target_path)
            shortcut_path = fix_path(shortcut_path)
            # Извлекаем имя процесса
            process_name = get_process_name(target_path)
        except Exception as e:
            logger.info(f"Ошибка при извлечении пути из ярлыка {filename}: {e}")

        if action == 'open':
            open_link(filename, target_path, args_list)
        if action == 'close':
            close_link(filename)

    # Обработка .url файлов (Steam и Epic Games)
    if filename.endswith(".url"):
        try:
            game_id_or_url = read_url_shortcut(shortcut_path)
            if not game_id_or_url:
                logger.info(f"Не удалось извлечь game_id или URL из файла {filename}")
        except Exception as e:
            logger.info(f"Ошибка при чтении .url файла {filename}: {e}")

        if action == 'open':
            open_url_link(game_id_or_url, filename)  # Передаём game_id или URL
        if action == 'close':
            close_link(filename)


def handler_folder(folder_path, action):
    """
    Обработчик команд для открытия и закрытия папок
    :param folder_path: путь к папке
    :param action: действие(open or close)
    """
    settings_file = os.path.join(get_base_directory(), 'user_settings', "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    if action == 'open':
        os.startfile(folder_path)
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths['start_folder']
        react(start_folder)
    if action == 'close':
        windows = gw.getAllTitles()  # Получаем все заголовки открытых окон
        folder_title = os.path.basename(folder_path)  # Получаем название папки
        try:
            for title in windows:
                if folder_title in title:  # Проверяем, содержится ли название папки в заголовке окна
                    window = gw.getWindowsWithTitle(title)[0]  # Получаем окно по заголовку
                    window.close()  # Закрываем окно
                    audio_paths = get_audio_paths(speaker)
                    close_folder = audio_paths['close_folder']
                    react(close_folder)
                    break
        except IndexError:
            audio_paths = get_audio_paths(speaker)
            error_file = audio_paths['error_file']
            react_detail(error_file)
            logger.error("Окно с указанным заголовком не найдено.")


def open_url_link(game_id_or_url, filename):
    """
    Функция для открытия ярлыков (.url)
    :param game_id_or_url: id игры извлекается из ярлыка
    :param filename: Имя файла
    """
    settings_file = os.path.join(get_base_directory(), 'user_settings', "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    steam_path = get_steam_path(settings_file)

    try:
        # Проверяем, является ли game_id_or_url URL Epic Games
        if game_id_or_url.startswith("com.epicgames.launcher://"):
            # Проверяем, есть ли уже сохраненные процессы для этой игры
            existing_processes = get_process_names_from_file(filename)
            audio_paths = get_audio_paths(speaker)
            logger.info(f"Запуск {filename} через Epic Games Launcher")
            if existing_processes:
                logger.info(f"Используем существующие процессы для игры '{filename}': {existing_processes}")
                # Открываем URL через стандартный механизм
                subprocess.Popen(["start", game_id_or_url], shell=True)
                start_folder = audio_paths['start_folder']
                react(start_folder)
            else:
                audio_paths = get_audio_paths(speaker)
                wait_load_file = audio_paths['wait_load_file']
                react_detail(wait_load_file)
                # Если процессов нет, собираем их
                before_processes = get_all_processes()
                # Открываем URL через стандартный механизм
                subprocess.Popen(["start", game_id_or_url], shell=True)
                # Ждем несколько секунд, чтобы процесс успел запуститься
                time.sleep(40)
                # Собираем процессы после запуска
                after_processes = get_all_processes()
                # Находим все новые процессы
                new_processes = find_new_processes(before_processes, after_processes)
                if new_processes:
                    logger.info(f"Новые процессы: {new_processes}")
                    save_process_names(filename, new_processes)  # Сохраняем все новые процессы
                    audio_paths = get_audio_paths(speaker)
                    done_load_file = audio_paths['done_load_file']
                    react_detail(done_load_file)
                else:
                    logger.error("Не удалось определить новые процессы.")
        else:
            # Иначе считаем, что это Steam-игра
            logger.info(f"Запуск игры через Steam: {game_id_or_url}")
            subprocess.Popen([steam_path, '-applaunch', game_id_or_url], shell=True)
            # Проверяем, есть ли уже сохраненные процессы для этой игры
            existing_processes = get_process_names_from_file(filename)
            audio_paths = get_audio_paths(speaker)
            if existing_processes:
                logger.info(f"Используем существующие процессы для игры '{filename}': {existing_processes}")
                if game_id_or_url == '252490' and speaker == 'sanboy':
                    start_rust = audio_paths['start_rust']
                    react_detail(start_rust)
                # Запускаем игру через Steam
                subprocess.Popen([steam_path, '-applaunch', game_id_or_url], shell=True)
                start_folder = audio_paths['start_folder']
                react(start_folder)
            else:
                audio_paths = get_audio_paths(speaker)
                wait_load_file = audio_paths['wait_load_file']
                react_detail(wait_load_file)
                # Если процессов нет, собираем их
                before_processes = get_all_processes()
                # Запускаем игру через Steam
                subprocess.Popen([steam_path, '-applaunch', game_id_or_url], shell=True)
                # Ждем несколько секунд, чтобы процесс успел запуститься
                time.sleep(40)
                # Собираем процессы после запуска
                after_processes = get_all_processes()
                # Находим все новые процессы
                new_processes = find_new_processes(before_processes, after_processes)
                if new_processes:
                    logger.info(f"Новые процессы: {new_processes}")
                    save_process_names(filename, new_processes)  # Сохраняем все новые процессы
                    audio_paths = get_audio_paths(speaker)
                    done_load_file = audio_paths['done_load_file']
                    react_detail(done_load_file)
                else:
                    logger.error("Не удалось определить новые процессы.")
    except Exception as e:
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths['error_file']
        react_detail(error_file)
        logger.error(f"Ошибка при открытии игры через Steam: {e}")


def open_link(filename, target_path, arguments):
    """
    Функция для открытия обычных ярлыков (.lnk)
    :param arguments: Аргументы из ярлыка
    :param filename: Имя файла
    :param target_path: Путь к исполняемому файлу (берется из ярлыка)
    """
    settings_file = os.path.join(get_base_directory(), 'user_settings', "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    try:
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths['start_folder']
        react(start_folder)

        # Проверяем, есть ли уже сохраненные процессы для этой игры
        existing_processes = get_process_names_from_file(filename)

        if existing_processes:
            logger.info(f"Используем существующие процессы для игры '{filename}': {existing_processes}")
            # Запускаем программу
            subprocess.Popen([target_path] + arguments, shell=True)
        else:
            audio_paths = get_audio_paths(speaker)
            wait_load_file = audio_paths['wait_load_file']
            react_detail(wait_load_file)
            # Если процессов нет, собираем их
            before_processes = get_all_processes()

            # Запускаем программу
            subprocess.Popen([target_path] + arguments, shell=True)

            # Ждем несколько секунд, чтобы процессы успели запуститься
            time.sleep(40)

            # Собираем процессы после запуска
            after_processes = get_all_processes()

            # Находим все новые процессы
            new_processes = find_new_processes(before_processes, after_processes)

            if new_processes:
                logger.info(f"Новые процессы: {new_processes}")
                save_process_names(filename, new_processes)  # Сохраняем все новые процессы
                audio_paths = get_audio_paths(speaker)
                done_load_file = audio_paths['done_load_file']
                react_detail(done_load_file)
            else:
                logger.error("Не удалось определить новые процессы.")

    except Exception as e:
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths['error_file']
        react_detail(error_file)
        logger.error(f"Ошибка при открытии программы: {e}")


def close_link(filename):
    """
    Функция для закрытия программы
    :param filename: Имя файла
    """
    settings_file = os.path.join(get_base_directory(), 'user_settings', "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    process_names = get_process_names_from_file(filename)  # Читаем имена процессов из файла
    if process_names:
        for process_name in process_names:
            close_program(process_name)  # Завершаем каждый процесс по имени
    else:
        logger.error("Имена процессов не найдены.")
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths['error_file']
        react_detail(error_file)
    audio_paths = get_audio_paths(speaker)
    close_folder = audio_paths['close_folder']
    react(close_folder)
    logger.info("Все процессы завершены.")

