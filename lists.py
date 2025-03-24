import os
import sys

def get_audio_paths(speaker):
    """
    Функция для создания путей к аудиофайлам
    :param speaker: Имя голоса
    :return:
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

    # Полный путь к папке с голосами
    base_path_to = os.path.join(base_path, 'speak_voice', speaker)

    # Пути к папкам с аудиофайлами
    what_folder = os.path.join(base_path_to, 'what')
    start_folder = os.path.join(base_path_to, 'start')
    approve_folder = os.path.join(base_path_to, 'approve')
    close_folder = os.path.join(base_path_to, 'close')
    start_greet_folder = os.path.join(base_path_to, 'start_greet', 'other')
    greet_folder = os.path.join(base_path_to, 'start_greet')
    other_folder = os.path.join(base_path_to, 'other')
    echo_folder = os.path.join(base_path_to, 'echo')
    close_assist_folder = os.path.join(base_path_to, 'close_assist')
    player_folder = os.path.join(base_path_to, 'player')
    censored_folder = os.path.join(base_path_to, 'censored')

    # Пути к файлам
    morning_greet = os.path.join(greet_folder, 'с добрым утром.ogg')
    evening_greet = os.path.join(greet_folder, 'добрый вечер.ogg')
    error_file = os.path.join(other_folder, 'произошла ошибка.ogg')
    off_file = os.path.join(other_folder, 'выключаю комп.ogg')
    del_file = os.path.join(other_folder, 'файл удален.ogg')
    restart_file = os.path.join(other_folder, 'я ненадолго.ogg')
    wait_load_file = os.path.join(other_folder, 'подожди. собираю данные о процессах.ogg')
    done_load_file = os.path.join(other_folder, 'процессы записаны.ogg')
    start_rust = os.path.join(other_folder, 'я в раст не пойду.ogg')
    prorok_sanboy = os.path.join(other_folder, 'пророк санбой.ogg')
    update_button = os.path.join(other_folder, 'еще не готово.ogg')
    what_command = os.path.join(other_folder, 'не понял команду.ogg')

    return {
        'what_folder': what_folder,
        'start_folder': start_folder,
        'approve_folder': approve_folder,
        'close_folder': close_folder,
        'start_greet_folder': start_greet_folder,
        'other_folder': other_folder,
        'echo_folder': echo_folder,
        'close_assist_folder': close_assist_folder,
        'player_folder': player_folder,
        'error_file': error_file,
        'off_file': off_file,
        'del_file': del_file,
        'restart_file': restart_file,
        'wait_load_file': wait_load_file,
        'done_load_file': done_load_file,
        'start_rust': start_rust,
        'prorok_sanboy': prorok_sanboy,
        'censored_folder': censored_folder,
        'update_button': update_button,
        'morning_greet': morning_greet,
        'evening_greet': evening_greet,
        'what_command': what_command
    }
