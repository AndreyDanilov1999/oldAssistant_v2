"""
Модуль с основными функциями: поиск в яндекс, выключение компа
"""
from lists import get_audio_paths
from func_list import get_current_speaker, get_base_directory
import os
from logging_config import logger
import subprocess
import webbrowser
import pygetwindow as gw
from speak_functions import react_detail, react

settings_file = os.path.join(get_base_directory(), 'user_settings', "settings.json")  # Полный путь к файлу настроек
speaker = get_current_speaker(settings_file)  # Получаем текущий голос


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
    audio_paths = get_audio_paths(speaker)
    off_file = audio_paths['off_file']
    react_detail(off_file)
    subprocess.run(["shutdown", "/s", "/t", "0"])

def open_volume_mixer():
    """ Открывает микшер виндовс """
    try:
        subprocess.Popen(["sndvol.exe", "/R"])
        logger.info("Микшер громкости открыт.")
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        if start_folder:
            react(start_folder)
    except Exception as e:
        logger.error(f"Ошибка при открытии микшера громкости: {e}", exc_info=True)
