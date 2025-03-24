"""
Модуль с основными функциями: поиск в яндекс, выключение компа
"""
from datetime import datetime
from lists import get_audio_paths
from func_list import get_current_speaker, get_base_directory
import os
from logging_config import logger
import subprocess
import webbrowser
from speak_functions import react_detail, react

settings_file = os.path.join(get_base_directory(), 'user_settings', "settings.json")  # Полный путь к файлу настроек


def search_yandex(query):
    """
    Поиск в инете по запросу
    :param query: запрос
    """
    url = f"https://www.ya.ru/search?text={query}"
    logger.info(f"Поиск по значению: {query}")
    webbrowser.open(url)

def shutdown_windows():
    """
    Выключение компа
    """
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    audio_paths = get_audio_paths(speaker)
    off_file = audio_paths['off_file']
    react_detail(off_file)
    subprocess.run(["shutdown", "/s", "/t", "0"])

def restart_windows():
    """
    Выключение компа
    """
    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    audio_paths = get_audio_paths(speaker)
    off_file = audio_paths['off_file']
    react_detail(off_file)
    subprocess.run(["shutdown", "/r", "/t", "0"])

def open_volume_mixer():
    """ Открывает микшер виндовс """
    try:
        subprocess.Popen(["sndvol.exe", "/R"])
        logger.info("Микшер громкости открыт")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        react_detail(error_file)
        logger.error(f"Ошибка при открытии микшера громкости: {e}", exc_info=True)

def close_volume_mixer():
    """ Открывает микшер виндовс """
    try:
        subprocess.run(['taskkill', '/IM', 'sndvol.exe', '/F'], check=True)
        logger.info("Микшер громкости закрыт")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        react_detail(error_file)
        logger.error(f"Ошибка при закрытии микшера громкости: {e}", exc_info=True)

def open_calc():
    """ Открывает калькулятор """
    try:
        subprocess.Popen(["calc.exe", "/R"])
        logger.info("Калькулятор открыт")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        react_detail(error_file)
        logger.error(f"Ошибка при открытии калькулятора {e}", exc_info=True)

def close_calc():
    """ Закрывает калькулятор """
    try:
        subprocess.run(['taskkill', '/IM', 'CalculatorApp.exe', '/F'], check=True)
        logger.info(f"Процесс успешно завершен.")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        react_detail(error_file)
        logger.error(f"Ошибка: {e}")

def open_paint():
    """ Открывает paint """
    try:
        subprocess.Popen("mspaint.exe")
        logger.info("Paint открыт")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        react_detail(error_file)
        logger.error(f"Ошибка при открытии paint {e}", exc_info=True)

def close_paint():
    """ Закрывает paint """
    try:
        subprocess.run(['taskkill', '/IM', 'mspaint.exe', '/F'], check=True)
        logger.info(f"Процесс успешно завершен.")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        react_detail(error_file)
        logger.error(f"Ошибка: {e}")

def open_path():
    try:
        # Открыть окно "Переменные среды"
        subprocess.run("rundll32 sysdm.cpl,EditEnvironmentVariables")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        react_detail(error_file)
        logger.error(f"Ошибка {e}", exc_info=True)

def greeting():
    # Получаем текущий час
    current_hour = datetime.now().hour

    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    audio_paths = get_audio_paths(speaker)

    # Определяем, какое приветствие воспроизвести
    if 4 <= current_hour < 11:
        react_detail(audio_paths['morning_greet'])
    elif 11 <= current_hour < 18:
        react(audio_paths['start_greet_folder'])
    else:
        react_detail(audio_paths['evening_greet'])

def open_taskmgr():
    """ Открывает Диспетчер задач """
    try:
        subprocess.Popen("taskmgr.exe")
        logger.info("Диспетчер задач открыт")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        react_detail(error_file)
        logger.error(f"Ошибка: {e}", exc_info=True)

def close_taskmgr():
    """ Закрывает Диспетчер задач """
    try:
        subprocess.run(['taskkill', '/IM', 'taskmgr.exe', '/F'], check=True)
        logger.info(f"Процесс успешно завершен.")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        react_detail(error_file)
        logger.error(f"Ошибка: {e}")

