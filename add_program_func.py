import os
import re
import json
import sys
import psutil
from win32com.client import Dispatch
from lists import get_audio_paths
import subprocess
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
    settings_file = os.path.join(get_base_directory(), "settings.json")  # Полный путь к файлу настроек
    settings = load_settings(settings_file)
    return settings.get("voice", "rogue")  # Возвращаем голос или значение по умолчанию

settings_file = os.path.join(get_base_directory(), "settings.json")  # Полный путь к файлу настроек
speaker = get_current_speaker(settings_file)  # Получаем текущий голос

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
    """Читает .url файл и извлекает game_id."""
    try:
        with open(url_path, 'r', encoding='utf-8') as file:
            content = file.read()

        for line in content.splitlines():
            if line.startswith('URL='):
                return line[22:]  # Возвращаем значение после "URL="
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
        process_names_file = os.path.join(get_base_directory(), 'process_names.json')  # Полный путь к файлу

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
        process_names_file = os.path.join(get_base_directory(), 'process_names.json')  # Полный путь к файлу

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


def add_function():
    root_folder = os.path.join(get_base_directory(), "links for assist")  # Полный путь к папке с ярлыками
    functions_file = os.path.join(get_base_directory(), "function_list.py")  # Полный путь к файлу с функциями

    # Проверяем, существует ли файл с функциями
    if not os.path.exists(functions_file):
        with open(functions_file, "w", encoding="utf-8") as file:
            file.write("# Автоматически сгенерированные функции\n\n")

    # Читаем уже существующие функции, чтобы избежать дублирования
    with open(functions_file, "r", encoding="utf-8") as file:
        existing_functions = file.read()

    # Список для хранения имен функций, которые были созданы ранее
    existing_shortcuts = set()

    # Поиск имен функций, которые уже существуют в файле
    for line in existing_functions.splitlines():
        if line.startswith("def open_"):
            function_name = line.split("def ")[1].split("(")[0]
            shortcut_name = function_name.replace("open_", "")
            existing_shortcuts.add(shortcut_name)

    # Поиск новых ярлыков в директории
    current_shortcuts = set()
    for filename in os.listdir(root_folder):
        if filename.endswith(".lnk") or filename.endswith(".url"):
            # Получаем имя файла без расширения
            function_name = os.path.splitext(filename)[0]
            function_name = re.sub(r'\W+', '_', function_name)  # Заменяем спецсимволы на _
            current_shortcuts.add(function_name)

            # Формируем имена функций для открытия и закрытия
            open_function_name = f"open_{function_name}"
            close_function_name = f"close_{function_name}"

            # Проверяем, существуют ли функции с такими именами
            if f"def {open_function_name}(" not in existing_functions \
                    and f"def {close_function_name}(" not in existing_functions:
                # Получаем путь к ярлыку
                shortcut_path = os.path.join(root_folder, filename)

                # Обработка .lnk файлов
                if filename.endswith(".lnk"):
                    try:
                        target_path, arguments = get_target_path(shortcut_path)
                        # Исправляем пути
                        target_path = fix_path(target_path)
                        shortcut_path = fix_path(shortcut_path)
                        # Извлекаем имя процесса
                        process_name = get_process_name(target_path)
                    except Exception as e:
                        logger.error(f"Ошибка при извлечении пути из ярлыка {filename}: {e}")
                        continue

                    # Основа для обычных ярлыков
                    open_function_code = f"""
def {open_function_name}():
    settings_file = os.path.join(get_base_directory(), "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    try:
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths['start_folder']
        react(start_folder)

        # Проверяем, есть ли уже сохраненные процессы для этой игры
        existing_processes = get_process_names_from_file('{function_name}')

        if existing_processes:
            logger.info(f"Используем существующие процессы для игры '{function_name}': {{existing_processes}}")
            # Запускаем программу
            subprocess.Popen(['{target_path}'], shell=True)
        else:
            # Если процессов нет, собираем их
            before_processes = get_all_processes()

            # Запускаем программу
            subprocess.Popen(['{target_path}'], shell=True)

            # Ждем несколько секунд, чтобы процессы успели запуститься
            time.sleep(20)

            # Собираем процессы после запуска
            after_processes = get_all_processes()

            # Находим все новые процессы
            new_processes = find_new_processes(before_processes, after_processes)

            if new_processes:
                save_process_names('{function_name}', new_processes)  # Сохраняем все новые процессы
                react(start_folder)
            else:
                logger.error("Не удалось определить новые процессы.")
    except Exception as e:
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths['error_file']
        react_detail(error_file)
        logger.error(f"Ошибка при открытии программы: {{e}}")
"""
                    # Создаем код для функции закрытия
                    close_function_code = f"""
def {close_function_name}():
    settings_file = os.path.join(get_base_directory(), "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    process_names = get_process_names_from_file('{function_name}')  # Читаем имена процессов из файла    
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
"""

                # Обработка .url файлов (Steam-игры)
                elif filename.endswith(".url"):
                    try:
                        game_id = read_url_shortcut(shortcut_path)
                        if not game_id:
                            logger.error(f"Не удалось извлечь game_id из файла {filename}")
                            continue
                    except Exception as e:
                        logger.error(f"Ошибка при чтении .url файла {filename}: {e}")
                        continue

                    # Основа для Steam-игр
                    open_function_code = f"""
def {open_function_name}():
    settings_file = os.path.join(get_base_directory(), "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    
    try:
        # Проверяем, есть ли уже сохраненные процессы для этой игры
        existing_processes = get_process_names_from_file('{function_name}')
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths['start_folder']
        react(start_folder)
        if existing_processes:
            logger.info(f"Используем существующие процессы для игры '{function_name}': {{existing_processes}}")

            # Запускаем игру через Steam
            steam_path = 'D:/Steam/steam.exe'
            subprocess.Popen([steam_path, '-applaunch', '{game_id}'], shell=True)
        else:
            # Если процессов нет, собираем их
            before_processes = get_all_processes()

            # Запускаем игру через Steam
            steam_path = 'D:/Steam/steam.exe'
            subprocess.Popen([steam_path, '-applaunch', '{game_id}'], shell=True)

            # Ждем несколько секунд, чтобы процесс успел запуститься
            time.sleep(30)

            # Собираем процессы после запуска
            after_processes = get_all_processes()

            # Находим все новые процессы
            new_processes = find_new_processes(before_processes, after_processes)

            if new_processes:
                logger.info(f"Новые процессы: {{new_processes}}")
                save_process_names('{function_name}', new_processes)  # Сохраняем все новые процессы
            else:
                logger.error("Не удалось определить новые процессы.")
    except Exception as e:
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths['error_file']
        react_detail(error_file)
        logger.error(f"Ошибка при открытии игры через Steam: {{e}}")
"""

                    # Для Steam-игр функция закрытия
                    close_function_code = f"""
def {close_function_name}():
    settings_file = os.path.join(get_base_directory(), "settings.json")  # Полный путь к файлу настроек
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    
    process_names = get_process_names_from_file('{function_name}')  # Читаем имена процессов из файла
    if process_names:
        for process_name in process_names:
            close_program(process_name)
    else:
        logger.error("Имена процессов не найдены.")
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths['error_file']
        react_detail(error_file)
    audio_paths = get_audio_paths(speaker)
    close_folder = audio_paths['close_folder']
    react(close_folder)
    logger.info("Все процессы завершены.")
"""

                # Добавляем новые функции в файл
                with open(functions_file, "a", encoding="utf-8") as file:
                    file.write(open_function_code + "\n")
                    file.write(close_function_code + "\n")

                audio_paths = get_audio_paths(speaker)
                add_func_file = audio_paths['add_func_file']
                react_detail(add_func_file)
                logger.info(f"Добавлены новые функции: {open_function_name} и {close_function_name}")

                # Проверяем, есть ли ярлыки, которые были раньше, но теперь отсутствуют
                missing_shortcuts = existing_shortcuts - current_shortcuts

                # Обработка отсутствующих ярлыков
                if missing_shortcuts:
                    for shortcut in missing_shortcuts:
                        open_function_name = f"open_{shortcut}"
                        close_function_name = f"close_{shortcut}"

                        # Заменяем тело функций на сообщение об удалении
                        new_body = '    react_detail(del_file)'

                        def replace_function_in_file(file_path, function_name, new_body):
                            """
                            Заменяет тело функции в файле на новое тело.
                            :param file_path: Путь к файлу.
                            :param function_name: Имя функции, которую нужно заменить.
                            :param new_body: Новое тело функции (строка).
                            """
                            with open(file_path, "r", encoding="utf-8") as file:
                                content = file.read()

                            # Регулярное выражение для поиска всей функции
                            pattern = re.compile(
                                rf"(def {function_name}$$$.*?$$$:\n)(.*?)(?=\n\s*def|\Z)",
                                re.DOTALL  # Режим многострочного поиска
                            )

                            # Заменяем тело функции
                            new_content = pattern.sub(rf"\1{new_body}", content)

                            # Записываем обновленный контент в файл
                            with open(file_path, "w", encoding="utf-8") as file:
                                file.write(new_content)

                        replace_function_in_file(functions_file, open_function_name, new_body)
                        replace_function_in_file(functions_file, close_function_name, new_body)

                        audio_paths = get_audio_paths(speaker)
                        check_func_file = audio_paths['check_func_file']
                        react_detail(check_func_file)
                        logger.info(f"Функции {open_function_name} и {close_function_name} обновлены в файле.")

    # Озвучиваем успешное создание функций
    audio_paths = get_audio_paths(speaker)
    check_file = audio_paths['check_file']
    react_detail(check_file)
