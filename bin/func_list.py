"""
Функции для запуска и закрытия программ и игр
"""
import json
import os
import shlex
import shutil
import subprocess
import threading
import time
import psutil
import pygetwindow as gw
from win32com.client import Dispatch
from bin.lists import get_audio_paths
from logging_config import logger, debug_logger
from bin.speak_functions import react, react_detail
from path_builder import get_path

def load_settings(settings_file):
    """Загрузка настроек из файла"""
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings  # Возвращаем все настройки
        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл {settings_file} содержит некорректный JSON.")
            debug_logger.error(f"Ошибка: файл {settings_file} содержит некорректный JSON.")
    else:
        logger.error(f"Файл настроек {settings_file} не найден.")
        debug_logger.error(f"Файл настроек {settings_file} не найден.")

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
        return shortcut.Targetpath, shortcut.Arguments, shortcut.WorkingDirectory
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных из ярлыка {shortcut_path}: {e}")
        debug_logger.error(f"Ошибка при извлечении данных из ярлыка {shortcut_path}: {e}")
        return None, None, None


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
        process_names_file = get_path('user_settings', 'process_names.json')

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
        debug_logger.info(f"Имена процессов для ярлыка '{shortcut_name}' сохранены в файл.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении имен процессов: {e}")
        debug_logger.error(f"Ошибка при сохранении имен процессов: {e}")


def get_process_names_from_file(shortcut_name):
    """Возвращает список имен процессов для указанного ярлыка из файла."""
    try:
        process_names = []
        process_names_file = get_path('user_settings', 'process_names.json')
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
                    debug_logger.error("Ошибка: файл содержит некорректный JSON.")
        return process_names
    except Exception as e:
        logger.error(f"Ошибка при чтении имен процессов: {e}")
        debug_logger.error(f"Ошибка при чтении имен процессов: {e}")
        return []


def close_program(process_name):
    """Завершает все процессы с указанным именем."""
    try:
        result = subprocess.run(
            ['taskkill', '/IM', process_name, '/F'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='cp866'
        )
        debug_logger.info(f"Вывод subprocess:{result.stdout.strip()}. Ошибки:{result.stderr.strip()}")
        # subprocess.run(['taskkill', '/IM', process_name, '/F'], check=True)
        debug_logger.info(f"Процесс {process_name} успешно завершен.")
    except subprocess.CalledProcessError:
        logger.error(f"Не удалось завершить процесс {process_name}.")
        debug_logger.error(f"Не удалось завершить процесс {process_name}.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        debug_logger.error(f"Ошибка: {e}")


def search_links():
    """
    Поиск ярлыков по ключевой папке
    Получение и сохранение имени ярлыков в json
    """
    root_folder = get_path('user_settings', "links for assist")  # Полный путь к папке с ярлыками
    root_links = get_path('user_settings', "links.json")

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
        debug_logger.info("Ярлыки сохранены в файле: %s", root_links)


def handler_links(filename, action):
    """
    Обработчик ярлыков в зависимости от их расширения
    """
    global game_id, target_path, process_name, game_id_or_url, args_list, workdir
    root_folder = get_path('user_settings', "links for assist")
    # Получаем путь к ярлыку
    shortcut_path = os.path.join(root_folder, filename)

    # Обработка .lnk файлов
    if filename.endswith(".lnk"):
        try:
            target_path, arguments, workdir = get_target_path(shortcut_path)
            target_path = fix_path(target_path)

            # Правильное разбиение аргументов (учитывает кавычки)
            args_list = shlex.split(arguments) if arguments else []

            process_name = get_process_name(target_path)

            if action == 'open':
                open_link(filename, target_path, args_list, workdir)
            elif action == 'close':
                close_link(filename)
        except Exception as e:
            logger.info(f"Ошибка при извлечении пути из ярлыка {filename}: {e}")
            debug_logger.info(f"Ошибка при извлечении пути из ярлыка {filename}: {e}")

    # Обработка .url файлов (Steam и Epic Games)
    if filename.endswith(".url"):
        try:
            game_id_or_url = read_url_shortcut(shortcut_path)
            if not game_id_or_url:
                logger.info(f"Не удалось извлечь game_id или URL из файла {filename}")
                debug_logger.info(f"Не удалось извлечь game_id или URL из файла {filename}")
        except Exception as e:
            logger.info(f"Ошибка при чтении .url файла {filename}: {e}")
            debug_logger.info(f"Ошибка при чтении .url файла {filename}: {e}")

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
    settings_file = get_path('user_settings', "settings.json")  # Полный путь к файлу настроек
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
            debug_logger.error("Окно с указанным заголовком не найдено.")


def open_url_link(game_id_or_url, filename):
    """
    Функция для открытия ярлыков (.url)
    :param game_id_or_url: id игры извлекается из ярлыка
    :param filename: Имя файла
    """
    settings_file = get_path('user_settings', "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    steam_path = get_steam_path(settings_file)

    try:
        # Проверяем, является ли game_id_or_url URL Epic Games
        if game_id_or_url.startswith("com.epicgames.launcher://"):
            # Проверяем, есть ли уже сохраненные процессы для этой игры
            existing_processes = get_process_names_from_file(filename)
            audio_paths = get_audio_paths(speaker)
            logger.info(f"Запуск {filename} через Epic Games Launcher")
            debug_logger.info(f"Запуск {filename} через Epic Games Launcher")
            if existing_processes:
                debug_logger.info(f"Используем существующие процессы для игры '{filename}': {existing_processes}")
                # Открываем URL через стандартный механизм
                subprocess.Popen(["start", game_id_or_url], shell=True)
                start_folder = audio_paths['start_folder']
                react(start_folder)
            else:
                # Если процессов нет, собираем их
                before_processes = get_all_processes()
                # Открываем URL через стандартный механизм
                subprocess.Popen(["start", game_id_or_url], shell=True)
                # Ждем несколько секунд, чтобы процесс успел запуститься

                audio_paths = get_audio_paths(speaker)
                wait_load_file = audio_paths['wait_load_file']
                react_detail(wait_load_file)

                time.sleep(40)
                # Собираем процессы после запуска
                after_processes = get_all_processes()
                # Находим все новые процессы
                new_processes = find_new_processes(before_processes, after_processes)
                if new_processes:
                    debug_logger.info(f"Новые процессы: {new_processes}")
                    save_process_names(filename, new_processes)  # Сохраняем все новые процессы
                    audio_paths = get_audio_paths(speaker)
                    done_load_file = audio_paths['done_load_file']
                    react_detail(done_load_file)
                else:
                    logger.error("Не удалось определить новые процессы.")
                    debug_logger.error("Не удалось определить новые процессы.")
        else:
            # Иначе считаем, что это Steam-игра
            logger.info(f"Запуск игры через Steam: {game_id_or_url}")
            debug_logger.info(f"Запуск игры через Steam: {game_id_or_url}")
            subprocess.Popen([steam_path, '-applaunch', game_id_or_url], shell=True)
            # Проверяем, есть ли уже сохраненные процессы для этой игры
            existing_processes = get_process_names_from_file(filename)
            audio_paths = get_audio_paths(speaker)
            if existing_processes:
                debug_logger.info(f"Нашел процессы '{filename}': {existing_processes}")
                if game_id_or_url == '252490' and speaker == 'sanboy':
                    start_rust = audio_paths['start_rust']
                    react_detail(start_rust)
                # Запускаем игру через Steam
                # subprocess.Popen([steam_path, '-applaunch', game_id_or_url], shell=True)
                process = subprocess.Popen(
                    [steam_path, '-applaunch', game_id_or_url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )

                # Запускаем логирование в отдельных потоках
                threading.Thread(
                    target=log_stream,
                    args=(process.stdout, debug_logger),
                    daemon=True
                ).start()

                threading.Thread(
                    target=log_stream,
                    args=(process.stderr, debug_logger),
                    daemon=True
                ).start()

                start_folder = audio_paths['start_folder']
                react(start_folder)
            else:
                # Если процессов нет, собираем их
                before_processes = get_all_processes()
                # Запускаем игру через Steam
                # subprocess.Popen([steam_path, '-applaunch', game_id_or_url], shell=True)
                process = subprocess.Popen(
                    [steam_path, '-applaunch', game_id_or_url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )

                # Запускаем логирование в отдельных потоках
                threading.Thread(
                    target=log_stream,
                    args=(process.stdout, debug_logger),
                    daemon=True
                ).start()

                threading.Thread(
                    target=log_stream,
                    args=(process.stderr, debug_logger),
                    daemon=True
                ).start()

                audio_paths = get_audio_paths(speaker)
                wait_load_file = audio_paths['wait_load_file']
                react_detail(wait_load_file)

                time.sleep(40)
                # Собираем процессы после запуска
                after_processes = get_all_processes()
                # Находим все новые процессы
                new_processes = find_new_processes(before_processes, after_processes)
                if new_processes:
                    debug_logger.info(f"Новые процессы: {new_processes}")
                    save_process_names(filename, new_processes)  # Сохраняем все новые процессы
                    audio_paths = get_audio_paths(speaker)
                    done_load_file = audio_paths['done_load_file']
                    react_detail(done_load_file)
                else:
                    logger.error("Не удалось определить новые процессы.")
                    debug_logger.error("Не удалось определить новые процессы.")
    except Exception as e:
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths['error_file']
        react_detail(error_file)
        logger.error(f"Ошибка при открытии игры через Steam: {e}")
        debug_logger.error(f"Ошибка при открытии игры через Steam: {e}")


def open_link(filename, target_path, arguments, workdir):
    """
    Улучшенная функция для открытия ярлыков (.lnk) с проверкой целевого файла
    :param workdir: Рабочая директория из ярлыка
    :param filename: Имя файла ярлыка
    :param target_path: Путь к исполняемому файлу (из ярлыка)
    :param arguments: Аргументы командной строки (из ярлыка)
    """
    settings_file = get_path('user_settings', "settings.json")
    speaker = get_current_speaker(settings_file)
    audio_paths = get_audio_paths(speaker)

    try:
        # 1. Проверка существования целевого файла
        if not os.path.exists(target_path):
            error_msg = f"Целевой файл не существует: {target_path}"
            logger.error(error_msg)
            debug_logger.error(error_msg)
            react_detail(audio_paths['error_file'])
            return False

        # 2. Проверка доступности файла
        if not os.access(target_path, os.R_OK | os.X_OK):
            error_msg = f"Нет доступа к файлу: {target_path}"
            logger.error(error_msg)
            debug_logger.error(error_msg)
            react_detail(audio_paths['error_file'])
            return False

        if not workdir:
            workdir = os.path.dirname(target_path)

            # Формируем команду
        command = [target_path] + arguments

        # 3. Проверка существующих процессов
        existing_processes = get_process_names_from_file(filename)
        # 4. Запуск процесса
        process = subprocess.Popen(
            command,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )

        threading.Thread(
            target=log_stream,
            args=(process.stdout, debug_logger),
            daemon=True
        ).start()

        threading.Thread(
            target=log_stream,
            args=(process.stderr, debug_logger),
            daemon=True
        ).start()

        # 6. Обработка разных сценариев
        if existing_processes:
            debug_logger.info(f"Найдены процессы для '{filename}': {existing_processes}")
            start_folder = audio_paths['start_folder']
            react(start_folder)
        else:
            react_detail(audio_paths['wait_load_file'])
            before_processes = get_all_processes()

            # Ждем запуска процессов (с таймаутом)
            time.sleep(40)

            after_processes = get_all_processes()
            new_processes = find_new_processes(before_processes, after_processes)

            if new_processes:
                debug_logger.info(f"Обнаружены новые процессы: {new_processes}")
                save_process_names(filename, new_processes)
                react_detail(audio_paths['done_load_file'])
            else:
                error_msg = "Не удалось определить новые процессы после запуска"
                logger.warning(error_msg)
                debug_logger.warning(error_msg)
                react_detail(audio_paths['error_file'])

        return True

    except FileNotFoundError as e:
        error_msg = f"Файл не найден: {str(e)}"
        logger.error(error_msg)
        debug_logger.error(error_msg)
        react_detail(audio_paths['error_file'])
        return False

    except PermissionError as e:
        error_msg = f"Ошибка доступа: {str(e)}"
        logger.error(error_msg)
        debug_logger.error(error_msg)
        react_detail(audio_paths['error_file'])
        return False

    except subprocess.SubprocessError as e:
        error_msg = f"Ошибка запуска процесса: {str(e)}"
        logger.error(error_msg)
        debug_logger.error(error_msg)
        react_detail(audio_paths['error_file'])
        return False

    except Exception as e:
        error_msg = f"Неожиданная ошибка: {str(e)}"
        logger.error(error_msg)
        debug_logger.error(error_msg, exc_info=True)
        react_detail(audio_paths['error_file'])
        return False

def close_link(filename):
    """
    Функция для закрытия программы
    :param filename: Имя файла
    """
    settings_file = get_path('user_settings', "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    process_names = get_process_names_from_file(filename)  # Читаем имена процессов из файла
    if process_names:
        for process_name in process_names:
            close_program(process_name)  # Завершаем каждый процесс по имени
    else:
        logger.error("Имена процессов не найдены.")
        debug_logger.error("Имена процессов не найдены.")
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths['error_file']
        react_detail(error_file)
    audio_paths = get_audio_paths(speaker)
    close_folder = audio_paths['close_folder']
    react(close_folder)
    logger.info("Все процессы завершены.")
    debug_logger.info("Все процессы завершены.")

# Список исключаемых файлов
EXCLUDED_FILES = {
    "immersive control panel.lnk",
    "uninstall.lnk",
    "control panel.lnk",
    "корзина.lnk",
    "этот компьютер.lnk",
    "панель управления.lnk",
    "сеть.lnk",
    "документы.lnk"
}

def create_shortcut(target_path, shortcut_path, description=""):
    """Создаёт ярлык для target_path и сохраняет его в shortcut_path."""
    try:
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.Description = description
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.save()
        return True
    except Exception as e:
        debug_logger.error(f"Ошибка создания ярлыка {shortcut_path}: {str(e)}")
        return False


def should_skip_file(filename):
    """Проверяет, нужно ли пропускать файл"""
    return filename.lower() in EXCLUDED_FILES


def scan_programs_folder(target_dir):
    """
    Сканирует только папку Programs верхнего уровня (без подпапок)
    и копирует ярлыки/создаёт ярлыки для exe
    """
    programs_folder = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs')

    if not os.path.exists(programs_folder):
        debug_logger.warning(f"Папка Programs не найдена: {programs_folder}")
        return False

    debug_logger.info(f"Сканирую папку Programs: {programs_folder}")

    try:
        items = os.listdir(programs_folder)
    except PermissionError:
        debug_logger.error(f"Нет доступа к папке: {programs_folder}")
        return False

    for item in items:
        item_path = os.path.join(programs_folder, item)

        # Пропускаем подпапки
        if os.path.isdir(item_path):
            continue

        file_ext = os.path.splitext(item)[1].lower()

        if should_skip_file(item):
            debug_logger.info(f"Пропускаем системный файл: {item}")
            continue

        try:
            # Обрабатываем только .lnk и .exe
            if file_ext == '.lnk' or file_ext == ".url":
                # Копируем ярлык
                dest_path = os.path.join(target_dir, item)
                shutil.copy2(item_path, dest_path)
                debug_logger.info(f"Скопирован ярлык из Programs: {item}")
            elif file_ext == '.exe':
                # Создаём ярлык для exe
                shortcut_name = f"{os.path.splitext(item)[0]}.lnk"
                shortcut_path = os.path.join(target_dir, shortcut_name)

                if not os.path.exists(shortcut_path):
                    create_shortcut(item_path, shortcut_path)
                    debug_logger.info(f"Создан ярлык для exe из Programs: {item}")
        except Exception as e:
            debug_logger.error(f"Ошибка обработки {item}: {str(e)}")
            continue

    return True


def scan_desktop_folders(target_dir):
    """
    Сканирует рабочие столы (основной и OneDrive) с подпапками
    и копирует ярлыки/создаёт ярлыки для exe
    """
    desktop_paths = [
        os.path.join(os.environ["USERPROFILE"], "Desktop"),
        os.path.join(os.environ["USERPROFILE"], "OneDrive", "Desktop")
    ]

    for desktop_path in desktop_paths:
        if not os.path.exists(desktop_path):
            debug_logger.warning(f"Папка рабочего стола не найдена: {desktop_path}")
            continue

        debug_logger.info(f"Сканирую рабочий стол: {desktop_path}")

        for root, _, files in os.walk(desktop_path):
            for file in files:
                file_path = os.path.join(root, file)

                if should_skip_file(file):
                    debug_logger.info(f"Пропускаем системный файл: {file}")
                    continue

                file_ext = os.path.splitext(file)[1].lower()

                try:
                    if file_ext == ".lnk" or file_ext == ".url":
                        dest_path = os.path.join(target_dir, file)
                        shutil.copy2(file_path, dest_path)
                        debug_logger.info(f"Скопирован ярлык с рабочего стола: {file}")
                    elif file_ext == ".exe":
                        shortcut_name = f"{os.path.splitext(file)[0]}.lnk"
                        shortcut_path = os.path.join(target_dir, shortcut_name)

                        if not os.path.exists(shortcut_path):
                            create_shortcut(file_path, shortcut_path)
                            debug_logger.info(f"Создан ярлык для exe с рабочего стола: {file}")
                except Exception as e:
                    debug_logger.error(f"Ошибка обработки {file}: {str(e)}")
                    continue

    return True


def scan_and_copy_shortcuts():
    """Основная функция сканирования (оба метода)"""
    target_dir = get_path("user_settings", "links for assist")

    if not os.path.exists(target_dir):
        try:
            os.makedirs(target_dir)
        except PermissionError:
            debug_logger.error(f"Нет прав на создание папки: {target_dir}")
            return False

    # Сканируем папку Programs без подпапок
    scan_programs_folder(target_dir)

    # Сканируем рабочие столы с подпапками
    scan_desktop_folders(target_dir)

    debug_logger.info(f"Готово! Ярлыки сохранены в: {target_dir}")
    return True

def log_stream(stream, logger):
    for line in stream:
        logger.info(line.decode('cp866', errors='replace').strip())
