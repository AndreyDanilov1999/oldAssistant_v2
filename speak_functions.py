import sys
import os
import random
from logging_config import logger

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Скрываем приветствие pygame
import pygame


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


pygame.mixer.init()


def react(folder_path, volume_reduction_factor=0.2):
    """
    Воспроизводит случайный аудиофайл из указанной папки.
    :param folder_path: Путь к папке с аудиофайлами.
    :param volume_reduction_factor: Коэффициент уменьшения громкости (по умолчанию 0.2).
    """
    try:
        # Получение списка файлов в папке
        audio_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.ogg')]

        if not audio_files:
            logger.info(f"В папке {folder_path} нет аудиофайлов.")
            return

        # Выбор случайного файла
        random_audio_file = random.choice(audio_files)
        random_filename = os.path.basename(random_audio_file)[:-4]
        logger.info(f"Ответ ассистента: {random_filename}")

        # Загрузка и воспроизведение аудиофайла
        pygame.mixer.music.load(random_audio_file)
        pygame.mixer.music.set_volume(volume_reduction_factor)  # Установка громкости
        pygame.mixer.music.play()

        # Ожидание завершения воспроизведения
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        logger.error(f"Ошибка при воспроизведении аудио: {e}")


def react_detail(file_path, volume_reduction_factor=0.2):
    """
    Воспроизводит указанный аудиофайл.
    :param file_path: Путь к аудиофайлу.
    :param volume_reduction_factor: Коэффициент уменьшения громкости (по умолчанию 0.2).
    """
    try:
        file_name = os.path.basename(file_path)[:-4]
        logger.info(f"Ответ ассистента: {file_name}")

        # Загрузка и воспроизведение аудиофайла
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.set_volume(volume_reduction_factor)  # Установка громкости
        pygame.mixer.music.play()

        # Ожидание завершения воспроизведения
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        logger.error(f"Ошибка при воспроизведении аудио: {e}")