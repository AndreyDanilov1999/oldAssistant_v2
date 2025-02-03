import time
from lists import get_audio_paths
from add_program_func import get_all_processes, find_new_processes, save_process_names, get_process_names_from_file, \
    close_program, get_current_speaker, get_base_directory
import os
from logging_config import logger
import subprocess
import sys
import webbrowser
from speak_functions import react, react_detail

settings_file = os.path.join(get_base_directory(), "settings.json")  # Полный путь к файлу настроек
speaker = get_current_speaker(settings_file)  # Получаем текущий голос

