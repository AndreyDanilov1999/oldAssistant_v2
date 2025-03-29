import os
import sys


def get_audio_paths(speaker):
    """
    Функция для создания путей к аудиофайлам с учетом структуры после сборки
    :param speaker: Имя голоса
    :return: Словарь с путями к аудиофайлам и папкам
    """
    # Получаем базовый путь с учетом всех возможных вариантов
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS  # onefile режим
        else:
            base_path = os.path.dirname(sys.executable)
            # Проверяем наличие _internal
            if os.path.exists(os.path.join(base_path, '_internal')):
                base_path = os.path.join(base_path, '_internal')
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    # Формируем путь к папке с голосом
    voice_base = os.path.join(base_path, 'bin', 'speak_voice', speaker) if not getattr(sys, 'frozen',
                                                                                       False) else os.path.join(
        base_path, 'speak_voice', speaker)

    # Проверяем существование пути (на случай разных вариантов сборки)
    if not os.path.exists(voice_base):
        # Пробуем альтернативный вариант пути
        alt_path = os.path.join(base_path, 'bin', 'speak_voice', speaker) \
            if getattr(sys, 'frozen', False) else os.path.join(base_path, 'speak_voice', speaker)
        if os.path.exists(alt_path):
            voice_base = alt_path

    # Создаем все необходимые пути
    paths = {
        'what_folder': os.path.join(voice_base, 'what'),
        'start_folder': os.path.join(voice_base, 'start'),
        'approve_folder': os.path.join(voice_base, 'approve'),
        'close_folder': os.path.join(voice_base, 'close'),
        'start_greet_folder': os.path.join(voice_base, 'start_greet', 'other'),
        'greet_folder': os.path.join(voice_base, 'start_greet'),
        'other_folder': os.path.join(voice_base, 'other'),
        'echo_folder': os.path.join(voice_base, 'echo'),
        'close_assist_folder': os.path.join(voice_base, 'close_assist'),
        'player_folder': os.path.join(voice_base, 'player'),
        'censored_folder': os.path.join(voice_base, 'censored'),

        # Аудиофайлы
        'morning_greet': os.path.join(voice_base, 'start_greet', 'с добрым утром.ogg'),
        'evening_greet': os.path.join(voice_base, 'start_greet', 'добрый вечер.ogg'),
        'error_file': os.path.join(voice_base, 'other', 'произошла ошибка.ogg'),
        'off_file': os.path.join(voice_base, 'other', 'выключаю комп.ogg'),
        'del_file': os.path.join(voice_base, 'other', 'файл удален.ogg'),
        'restart_file': os.path.join(voice_base, 'other', 'я ненадолго.ogg'),
        'wait_load_file': os.path.join(voice_base, 'other', 'подожди. собираю данные о процессах.ogg'),
        'done_load_file': os.path.join(voice_base, 'other', 'процессы записаны.ogg'),
        'start_rust': os.path.join(voice_base, 'other', 'я в раст не пойду.ogg'),
        'prorok_sanboy': os.path.join(voice_base, 'other', 'пророк санбой.ogg'),
        'update_button': os.path.join(voice_base, 'other', 'еще не готово.ogg'),
        'what_command': os.path.join(voice_base, 'other', 'не понял команду.ogg')
    }

    return paths
