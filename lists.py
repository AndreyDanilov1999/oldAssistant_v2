import os
import sys

def get_audio_paths(speaker):
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
    start_greet_folder = os.path.join(base_path_to, 'start_greet')
    other_folder = os.path.join(base_path_to, 'other')
    echo_folder = os.path.join(base_path_to, 'echo')
    close_assist_folder = os.path.join(base_path_to, 'close_assist')

    # Пути к файлам
    error_file = os.path.join(other_folder, 'произошла ошибка.ogg')
    off_file = os.path.join(other_folder, 'выключаю комп.ogg')
    del_file = os.path.join(other_folder, 'файл удален.ogg')
    cache_file = os.path.join(other_folder, 'кэш очищен, думаешь это поможет.ogg')
    restart_file = os.path.join(other_folder, 'я ненадолго.ogg')
    check_file = os.path.join(other_folder, 'файлы проверены.ogg')
    check_func_file = os.path.join(other_folder, 'некоторые функции были обновлены. возможно ярлык не найден.ogg')
    wait_load_file = os.path.join(other_folder, 'подожди. собираю данные о процессах.ogg')
    done_load_file = os.path.join(other_folder, 'процессы записаны.ogg')
    check_file_start = os.path.join(other_folder, 'подожди. проверяю папку с ярлыками.ogg')

    return {
        'what_folder': what_folder,
        'start_folder': start_folder,
        'approve_folder': approve_folder,
        'close_folder': close_folder,
        'start_greet_folder': start_greet_folder,
        'other_folder': other_folder,
        'echo_folder': echo_folder,
        'close_assist_folder': close_assist_folder,
        'error_file': error_file,
        'off_file': off_file,
        'del_file': del_file,
        'cache_file': cache_file,
        'restart_file': restart_file,
        'check_file': check_file,
        'check_func_file': check_func_file,
        'wait_load_file': wait_load_file,
        'done_load_file': done_load_file,
        'check_file_start': check_file_start,
    }
