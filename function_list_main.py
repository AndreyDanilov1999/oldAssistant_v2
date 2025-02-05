"""
Модуль с основными функциями: поиск в яндекс, выключение компа
"""
from lists import get_audio_paths
from func_list import get_current_speaker, get_base_directory
import os
from logging_config import logger
import subprocess
import webbrowser
from speak_functions import react_detail

settings_file = os.path.join(get_base_directory(), "settings.json")  # Полный путь к файлу настроек
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

