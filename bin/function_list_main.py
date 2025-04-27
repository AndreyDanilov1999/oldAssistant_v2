"""
Модуль с основными функциями: поиск в яндекс, выключение компа
"""
import os
from datetime import datetime
from bin.lists import get_audio_paths
from bin.func_list import get_current_speaker
from logging_config import logger, debug_logger
import subprocess
import webbrowser
from bin.speak_functions import thread_react_detail, thread_react, react_detail
from path_builder import get_path

settings_file = get_path('user_settings', "settings.json")

def search_yandex(query):
    """
    Поиск в инете по запросу
    :param query: запрос
    """
    url = f"https://www.ya.ru/search?text={query}"
    debug_logger.info(f"Поиск по значению: {query}")
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
        debug_logger.info("Микшер громкости открыт")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        thread_react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка при открытии микшера громкости: {e}", exc_info=True)
        debug_logger.error(f"Ошибка при открытии микшера громкости: {e}", exc_info=True)

def close_volume_mixer():
    """ Открывает микшер виндовс """
    try:
        result = subprocess.run(['taskkill', '/IM', 'sndvol.exe', '/F'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding='cp866',
                                check=True)
        debug_logger.info("Микшер громкости закрыт")
        debug_logger.info(f"Вывод subprocess:{result.stdout.strip()}. Ошибки:{result.stderr.strip()}")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        thread_react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка при закрытии микшера громкости: {e}", exc_info=True)
        debug_logger.error(f"Ошибка при закрытии микшера громкости: {e}", exc_info=True)
def open_calc():
    """ Открывает калькулятор """
    try:
        subprocess.Popen(["calc.exe", "/R"])
        debug_logger.info("Калькулятор открыт")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        thread_react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка при открытии калькулятора {e}", exc_info=True)
        debug_logger.error(f"Ошибка при открытии калькулятора {e}", exc_info=True)

def close_calc():
    """ Закрывает калькулятор """
    try:
        result = subprocess.run(['taskkill', '/IM', 'CalculatorApp.exe', '/F'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding='cp866',
                                check=True)
        debug_logger.info(f"Процесс успешно завершен.")
        debug_logger.info(f"Вывод subprocess:{result.stdout.strip()}. Ошибки:{result.stderr.strip()}")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        thread_react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка: {e}")
        debug_logger.error(f"Ошибка: {e}")

def open_paint():
    """ Открывает paint """
    try:
        subprocess.Popen("mspaint.exe")
        debug_logger.info("Paint открыт")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        thread_react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка при открытии paint {e}", exc_info=True)
        debug_logger.error(f"Ошибка при открытии paint {e}", exc_info=True)

def close_paint():
    """ Закрывает paint """
    try:
        result = subprocess.run(['taskkill', '/IM', 'mspaint.exe', '/F'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding='cp866',
                                check=True)
        debug_logger.info(f"Пейнт закрыт.")
        debug_logger.info(f"Вывод subprocess:{result.stdout.strip()}. Ошибки:{result.stderr.strip()}")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        thread_react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка: {e}")
        debug_logger.error(f"Ошибка: {e}")

def open_path():
    try:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        thread_react(start_folder)
        subprocess.run("rundll32 sysdm.cpl,EditEnvironmentVariables")
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка {e}", exc_info=True)
        debug_logger.error(f"Ошибка {e}", exc_info=True)

def greeting():
    # Получаем текущий час
    current_hour = datetime.now().hour

    speaker = get_current_speaker(settings_file)  # Получаем текущий голос
    audio_paths = get_audio_paths(speaker)

    # Определяем, какое приветствие воспроизвести
    if 4 <= current_hour < 11:
        thread_react_detail(audio_paths['morning_greet'])
    elif 11 <= current_hour < 18:
        thread_react(audio_paths['start_greet_folder'])
    else:
        thread_react_detail(audio_paths['evening_greet'])

def open_taskmgr():
    """ Открывает Диспетчер задач """
    try:
        subprocess.Popen("taskmgr.exe")
        debug_logger.info("Диспетчер задач открыт")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        thread_react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка: {e}", exc_info=True)
        debug_logger.error(f"Ошибка: {e}", exc_info=True)

def close_taskmgr():
    """ Закрывает Диспетчер задач """
    try:
        result = subprocess.run(['taskkill', '/IM', 'taskmgr.exe', '/F'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding='cp866',
                                check=True)
        debug_logger.info(f"Диспетчер задач открыт")
        debug_logger.info(f"Вывод subprocess:{result.stdout.strip()}. Ошибки:{result.stderr.strip()}")
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        thread_react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)  # Получаем текущий голос
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка: {e}")
        debug_logger.error(f"Ошибка: {e}")

def open_recycle_bin():
    """Открывает корзину"""
    try:
        # Используем explorer для открытия корзины
        subprocess.Popen('explorer.exe shell:RecycleBinFolder')
        debug_logger.info("Корзина открыта")
        speaker = get_current_speaker(settings_file)
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        thread_react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка при открытии корзины: {e}", exc_info=True)
        debug_logger.error(f"Ошибка при открытии корзины: {e}", exc_info=True)

def close_recycle_bin():
    """Закрывает все окна корзины"""
    try:
        # Закрываем все окна с заголовком "Корзина" (может отличаться в разных языковых версиях)
        result = subprocess.run(['taskkill', '/FI', 'WINDOWTITLE eq Корзина*', '/F'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding='cp866',
                                check=True)
        debug_logger.info("Корзина закрыта")
        debug_logger.info(f"Вывод subprocess:{result.stdout.strip()}. Ошибки:{result.stderr.strip()}")
        speaker = get_current_speaker(settings_file)
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        thread_react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка при закрытии корзины: {e}")
        debug_logger.error(f"Ошибка при закрытии корзины: {e}")

def open_appdata():
    """Открывает папку %appdata% (AppData/Roaming)"""
    try:
        # Полный путь к папке AppData/Roaming
        appdata_path = os.path.expandvars('%APPDATA%')

        # Открываем в проводнике
        subprocess.Popen(f'explorer "{appdata_path}"')

        debug_logger.info("Папка %appdata% открыта")
        speaker = get_current_speaker(settings_file)
        audio_paths = get_audio_paths(speaker)
        start_folder = audio_paths.get('start_folder')
        thread_react(start_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка при открытии %appdata%: {e}", exc_info=True)
        debug_logger.error(f"Ошибка при открытии %appdata%: {e}", exc_info=True)


def close_appdata():
    """Закрывает все окна проводника в папке %appdata%"""
    try:
        title_list = ['Roaming', 'AppData']
        for title in title_list:
            # Закрываем все окна проводника, открытые в этой папке
            result = subprocess.run(['taskkill', '/FI', f'WINDOWTITLE eq {title}*', '/F'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    encoding='cp866',
                                    check=True)

            debug_logger.info("Папка %appdata% закрыта")
            debug_logger.info(f"Вывод subprocess:{result.stdout.strip()}. Ошибки:{result.stderr.strip()}")
        speaker = get_current_speaker(settings_file)
        audio_paths = get_audio_paths(speaker)
        close_folder = audio_paths['close_folder']
        thread_react(close_folder)
    except Exception as e:
        speaker = get_current_speaker(settings_file)
        audio_paths = get_audio_paths(speaker)
        error_file = audio_paths.get('error_file')
        thread_react_detail(error_file)
        logger.error(f"Ошибка при закрытии %appdata%: {e}")
        debug_logger.error(f"Ошибка при закрытии %appdata%: {e}")