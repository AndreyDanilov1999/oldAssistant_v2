"""
Этот модуль представляет собой основной файл для работы ассистента.

Здесь реализованы функции и классы, необходимые для
запуска и управления ассистентом, включая обработку
пользовательского ввода и управление интерфейсом.
"""
import json
import logging
import os.path
import traceback
from func_list import search_links, handler_links, handler_folder
from function_list_main import *
import gc
import threading
import pyaudio
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, \
    QPushButton, QCheckBox, QSystemTrayIcon, QAction, qApp, QMenu, QMessageBox, \
    QTextEdit, QDialog, QLabel, QComboBox, QLineEdit, QListWidget, QListWidgetItem, QFileDialog, QColorDialog, \
    QInputDialog
from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer, QEvent, pyqtSignal
import subprocess
from script_audio import controller
from speak_functions import react, react_detail
from logging_config import logger
from lists import get_audio_paths
from vosk import Model, KaldiRecognizer


speakers = dict(Пласид='placide', Бестия='rogue', Джонни='johnny', Санбой='sanboy')


class Assistant(QWidget):
    """
Основной класс содержащий GUI и скрипт обработки команд
    """

    def get_base_directory(self):
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

    def __init__(self):
        super().__init__()
        self.styles = None
        self.log_file_path = os.path.join(self.get_base_directory(), 'assistant.log')
        self.init_logger()
        self.settings_file_path = os.path.join(self.get_base_directory(), 'settings.json')
        self.color_settings_path = os.path.join(self.get_base_directory(), 'color_settings.json')
        self.commands = self.load_commands(os.path.join(self.get_base_directory(), 'commands.json'))
        self.default_preset_style = os.path.join(self.get_base_directory(), 'presets', 'default.json')
        self.last_position = 0
        self.steam_path = self.load_steam_path()
        self.is_assistant_running = False
        self.assistant_thread = None
        self.speaker = self.load_settings()
        self.assistant_name = self.load_settings_name()
        self.audio_paths = get_audio_paths(self.speaker)
        self.version = "1.0.4"
        self.label_version = QLabel(f"Версия: {self.version}", self)
        self.label_message = QLabel('', self)
        self.initui()
        self.load_and_apply_styles()
        self.apply_styles()
        # Проверка автозапуска при старте программы
        self.check_autostart()
        self.hide()
        self.run_assist()

    def initui(self):
        """Инициализация пользовательского интерфейса."""
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()

        # Инициализируем QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(os.path.join(self.get_base_directory(), 'assist-min.ico')))

        show_action = QAction("Развернуть", self)
        show_action.triggered.connect(self.show)

        hide_action = QAction("Свернуть", self)
        hide_action.triggered.connect(self.hide)

        quit_action = QAction("Закрыть", self)
        quit_action.triggered.connect(self.close_app)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

        # Кнопка "Старт ассистента"
        self.start_button = QPushButton("Старт ассистента")
        self.start_button.clicked.connect(self.start_assist_toggle)
        left_layout.addWidget(self.start_button)

        # Чекбокс "Автозапуск"
        self.autostart_checkbox = QCheckBox("Автозапуск")
        self.autostart_checkbox.stateChanged.connect(self.toggle_autostart)
        left_layout.addWidget(self.autostart_checkbox)

        # Кнопка "Открыть папку с ярлыками"
        self.open_folder_button = QPushButton("Открыть папку с ярлыками")
        self.open_folder_button.clicked.connect(self.open_folder)
        left_layout.addWidget(self.open_folder_button)

        # Кнопка "Проверка ярлыков"
        self.check_shortcut_button = QPushButton("Проверка ярлыков")
        self.check_shortcut_button.clicked.connect(self.check_shortcuts)
        left_layout.addWidget(self.check_shortcut_button)

        # Кнопка "Настройки"
        self.settings_button = QPushButton("Настройки")
        self.settings_button.clicked.connect(self.open_settings)
        left_layout.addWidget(self.settings_button)

        # Кнопка "Оформление интерфейса"
        self.style_settings_button = QPushButton('Оформление интерфейса')
        self.style_settings_button.clicked.connect(self.open_color_settings)
        left_layout.addWidget(self.style_settings_button)

        # Кнопка "Очистить логи"
        self.clear_logs_button = QPushButton("Очистить логи")
        self.clear_logs_button.clicked.connect(self.clear_logs)
        left_layout.addWidget(self.clear_logs_button)

        # Кнопка "Добавить команду для программы"
        self.add_command_button = QPushButton("Создать команду для программы")
        self.add_command_button.clicked.connect(self.add_new_command)
        left_layout.addWidget(self.add_command_button)

        # Кнопка "Добавить команду для открытия папки"
        self.add_folder_button = QPushButton("Создать команду для папки")
        self.add_folder_button.clicked.connect(self.add_folder_command)
        left_layout.addWidget(self.add_folder_button)

        # Кнопка "Добавленные команды"
        self.added_commands_button = QPushButton("Добавленные команды")
        self.added_commands_button.clicked.connect(self.added_commands)
        left_layout.addWidget(self.added_commands_button)

        # Добавляем растяжку, чтобы кнопки были вверху
        left_layout.addStretch()

        left_layout.addWidget(self.label_version)

        # Правая часть (поле для логов)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)  # Запрещаем редактирование

        # Добавляем левую и правую части в основной макет
        main_layout.addLayout(left_layout, 1)
        main_layout.addWidget(self.log_area, 2)

        # Устанавливаем основной макет для окна
        self.setLayout(main_layout)

        # Настройки окна
        self.setWindowTitle("Виртуальный помощник")
        self.setGeometry(600, 300, 800, 500)

        # Установка иконки для окна
        self.setWindowIcon(QIcon(os.path.join(self.get_base_directory(), 'assist-min.ico')))

        # Инициализация FileSystemWatcher
        self.init_file_watcher()

        # Загрузка предыдущих записей из файла логов
        self.load_existing_logs()

        # Таймер для периодической проверки файла
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(1000)  # Проверка каждую секунду

    def init_logger(self):
        """Инициализация логгера."""
        # Используем ваш конфиг логов
        self.logger = logging.getLogger("assistant")

    def init_file_watcher(self):
        """Инициализация FileSystemWatcher для отслеживания изменений файла логов."""
        self.file_watcher = QFileSystemWatcher([self.log_file_path])
        self.file_watcher.fileChanged.connect(self.update_logs)

    def load_existing_logs(self):
        """Загрузка всех записей из файла логов при запуске."""
        try:
            if not os.path.exists(self.log_file_path):
                self.logger.info("Файл логов не найден. Создаем новый.")
                with open(self.log_file_path, "w", encoding="utf-8"):
                    pass  # Создаем пустой файл

            with open(self.log_file_path, "r", encoding="utf-8-sig", errors="replace") as file:
                existing_logs = file.read()
                self.log_area.append(existing_logs)
                self.last_position = file.tell()  # Сохраняем позицию последнего прочитанного байта
        except Exception as e:
            self.logger.error(f"Ошибка при чтении файла логов: {e}")
            self.log_area.append(f"Ошибка при чтении файла логов: {e}")

    def update_logs(self):
        """Обновление логов при изменении файла."""
        self.check_for_updates()

    def check_for_updates(self):
        """Проверка файла на наличие новых данных."""
        try:
            if not os.path.exists(self.log_file_path):
                self.logger.warning("Файл логов не найден. Пытаемся переподключиться...")
                self.file_watcher.removePath(self.log_file_path)
                self.file_watcher.addPath(self.log_file_path)
                return

            with open(self.log_file_path, "r", encoding="utf-8-sig", errors="replace") as file:
                file.seek(self.last_position)  # Переходим к последней прочитанной позиции
                new_lines = file.readlines()
                if new_lines:
                    self.text_append("".join(new_lines))
                    self.last_position = file.tell()
        except FileNotFoundError:
            self.logger.warning("Файл логов не найден, переподключаем FileSystemWatcher.")
            self.file_watcher.removePath(self.log_file_path)
            self.file_watcher.addPath(self.log_file_path)
        except Exception as e:
            self.logger.error(f"Ошибка при чтении файла логов: {e}")
            self.log_area.append(f"Ошибка при чтении файла логов: {e}")

    def text_append(self, text):
        """Добавление текста в QTextEdit с автоматической прокруткой."""
        self.log_area.append(text)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def load_and_apply_styles(self):
        """
        Загружает стили из файла и применяет их к элементам интерфейса.
        Если файл не найден или поврежден, устанавливает значения по умолчанию.
        """
        try:
            with open(self.color_settings_path, 'r') as file:
                self.styles = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            try:
                with open(self.default_preset_style, 'r') as default_file:
                    self.styles = json.load(default_file)
            except (FileNotFoundError, json.JSONDecodeError):
                self.styles = {}

        # Применяем загруженные или значения по умолчанию
        self.apply_styles()

    def apply_styles(self):
        # Применяем стили к текущему окну
        style_sheet = ""
        for widget, styles in self.styles.items():
            style_sheet += f"{widget} {{\n"
            for prop, value in styles.items():
                style_sheet += f"    {prop}: {value};\n"
            style_sheet += "}\n"

        # Устанавливаем стиль для текущего окна
        self.setStyleSheet(style_sheet)

        # Применяем стили для label_version и label_message
        if 'label_version' in self.styles:
            self.label_version.setStyleSheet(self.format_style(self.styles['label_version']))

        if 'label_message' in self.styles:
            self.label_message.setStyleSheet(self.format_style(self.styles['label_message']))

    def format_style(self, style_dict):
        """Форматируем словарь стиля в строку для setStyleSheet"""
        return '; '.join(f"{key}: {value}" for key, value in style_dict.items())

    def open_color_settings(self):
        """Открывает диалоговое окно для настройки цветов."""
        try:
            color_dialog = ColorSettingsWindow(self.styles, self.color_settings_path, self)
            color_dialog.colorChanged.connect(self.load_and_apply_styles)
            color_dialog.exec_()
        except Exception as e:
            logger.info(f"Ошибка при открытии окна настроек: {e}")

    def close_app(self):
        """Закрытие приложения."""
        self.stop_assist()
        qApp.quit()

    def load_commands(self, filename):
        """Загружает команды из JSON-файла."""
        file_path = os.path.join(self.get_base_directory(), filename)  # Полный путь к файлу
        try:
            if not os.path.exists(file_path):
                self.logger.info(f"Файл {file_path} не найден.")
                return {}  # Возвращаем пустой словарь, если файл не найден

            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()  # Читаем содержимое и убираем пробелы
                if not content:  # Если файл пустой
                    return {}  # Возвращаем пустой словарь
                return json.loads(content)  # Загружаем JSON
        except json.JSONDecodeError:
            self.logger.error(f"Ошибка: файл {file_path} содержит некорректный JSON.")
            return {}  # Возвращаем пустой словарь при ошибке декодирования
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке команд из файла {file_path}: {e}")
            return {}  # Возвращаем пустой словарь при других ошибках

    def load_settings(self):
        """Загрузка настроек из файла."""
        if os.path.exists(self.settings_file_path):
            try:
                with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('voice', 'rogue')  # Возвращаем значение по умолчанию, если ключ отсутствует
            except json.JSONDecodeError:
                self.logger.error(f"Ошибка: файл {self.settings_file_path} содержит некорректный JSON.")
        else:
            self.logger.error(f"Файл настроек {self.settings_file_path} не найден.")

        return 'rogue'  # Возвращаем значение по умолчанию, если файл не найден или ошибка

    def load_settings_name(self):
        """Загрузка имени ассистента из файла."""
        if os.path.exists(self.settings_file_path):
            try:
                with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('assistant_name',
                                        'джон')  # Возвращаем значение по умолчанию, если ключ отсутствует
            except json.JSONDecodeError:
                self.logger.error(f"Ошибка: файл {self.settings_file_path} содержит некорректный JSON.")
        else:
            self.logger.error(f"Файл настроек {self.settings_file_path} не найден.")

        return 'джон'  # Возвращаем значение по умолчанию, если файл не найден или ошибка

    def load_steam_path(self):
        """Загрузка пути steam.exe из файла."""
        if os.path.exists(self.settings_file_path):
            try:
                with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('steam_path',
                                        '')  # Возвращаем значение по умолчанию, если ключ отсутствует
            except json.JSONDecodeError:
                self.logger.error(f"Ошибка: файл {self.settings_file_path} содержит некорректный JSON.")
        else:
            self.logger.error(f"Файл настроек {self.settings_file_path} не найден.")

        return ''  # Возвращаем значение по умолчанию, если файл не найден или ошибка

    def save_settings(self):
        """Сохраняет настройки в файл settings.json."""
        settings_file = os.path.join(self.get_base_directory(), 'settings.json')
        settings_data = {
            "voice": self.speaker,
            "assistant_name": self.assistant_name,
            "steam_path": self.steam_path
        }
        with open(settings_file, 'w', encoding='utf-8') as file:
            json.dump(settings_data, file, ensure_ascii=False, indent=4)
        logger.info("Настройки сохранены.")

    def on_tray_icon_activated(self, reason):
        """Обработка активации иконки в трее."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.show()
            self.activateWindow()

    def changeEvent(self, event):
        """Обработка изменения состояния окна."""
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                self.hide()
        super().changeEvent(event)

    def closeEvent(self, event):
        """Обработка закрытия окна."""
        if self.is_assistant_running:
            dialog = QDialog(self)
            dialog.setWindowTitle('Подтверждение')
            dialog.setFixedSize(200, 110)

            main_layout = QVBoxLayout(dialog)

            self.label_message.setText('Вы уверены?')  # Устанавливаем текст в label_message
            self.label_message.setAlignment(Qt.AlignCenter)  # Центрируем текст
            main_layout.addWidget(self.label_message)  # Добавляем self.label_message в макет

            button_layout = QHBoxLayout()

            yes_button = QPushButton('Да', dialog)
            yes_button.setFixedSize(60, 25)
            no_button = QPushButton('Нет', dialog)
            no_button.setFixedSize(60, 25)

            yes_button.clicked.connect(lambda: self.handle_response(True, event, dialog))
            no_button.clicked.connect(lambda: self.handle_response(False, event, dialog))

            button_layout.addWidget(yes_button)
            button_layout.addWidget(no_button)

            # Центрируем кнопки
            button_layout.setAlignment(Qt.AlignCenter)

            # Добавляем горизонтальный макет кнопок в основной макет
            main_layout.addLayout(button_layout)

            # Обработка закрытия окна через крестик
            dialog.rejected.connect(lambda: self.handle_response(False, event, dialog))

            dialog.exec_()  # Отображаем диалоговое окно

    def handle_response(self, response, event, dialog):
        """Обработка ответа пользователя на подтверждение закрытия."""
        if response:
            self.stop_assist()
            qApp.quit()
        else:
            event.ignore()
        dialog.close()  # Закрываем диалоговое окно

    def start_assist_toggle(self):
        """Обработка нажатия кнопки 'Старт ассистента' или 'Остановить работу'"""
        if self.is_assistant_running:
            self.stop_assist()
        else:
            self.run_assist()

    def run_assist(self):
        """Запуск ассистента"""
        self.is_assistant_running = True
        self.start_button.setText("Остановить работу")  # Меняем текст кнопки
        self.log_area.append("Ассистент запущен...")  # Добавляем запись в лог

        # Запуск ассистента в отдельном потоке
        self.assistant_thread = threading.Thread(target=self.run_script)
        self.assistant_thread.start()

    def stop_assist(self):
        """Остановка ассистента"""
        self.is_assistant_running = False
        self.start_button.setText("Старт ассистента")  # Меняем текст кнопки
        self.log_area.append("Ассистент остановлен...")  # Добавляем запись в лог

        # Получаем пути для конкретного голоса
        audio_paths = get_audio_paths(self.speaker)
        close_assist_folder = audio_paths.get('close_assist_folder')

        if close_assist_folder:
            react(close_assist_folder)
        else:
            self.log_area.append("Ошибка: путь для закрытия ассистента не найден.")

        # Остановка ассистента
        if self.assistant_thread and self.assistant_thread.is_alive():
            self.assistant_thread.join()  # Ожидание завершения потока

    def run_script(self):
        """Основной цикл ассистента"""
        start_greet_folder = self.audio_paths.get('start_greet_folder')
        if start_greet_folder:
            react(start_greet_folder)

        try:
            logger.info('Попытка загрузки модели')
            for text in self.get_audio():
                if not self.is_assistant_running:  # Проверяем флаг is_assistant_running
                    break
                if self.assistant_name in text:
                    reaction_triggered = False

                    # Обработка команд на запуск
                    if any(keyword in text for keyword in ['запус', 'откр', 'вкл']):
                        # Пытаемся обработать команду через handle_app_command
                        app_command_success = self.handle_app_command(text, 'open')
                        # Пытаемся обработать команду через handle_folder_command
                        folder_command_success = self.handle_folder_command(text, 'open')
                        # Если ни одна команда не была успешно обработана, устанавливаем флаг
                        if not app_command_success and not folder_command_success:
                            reaction_triggered = True

                    # Обработка команд на закрытие
                    elif any(keyword in text for keyword in ['закр', 'выкл', 'выруб', 'отруб']):
                        # Пытаемся обработать команду через handle_app_command
                        app_command_success = self.handle_app_command(text, 'close')
                        # Пытаемся обработать команду через handle_folder_command
                        folder_command_success = self.handle_folder_command(text, 'close')
                        # Если ни одна команда не была успешно обработана, устанавливаем флаг
                        if not app_command_success and not folder_command_success:
                            reaction_triggered = True

                    elif "поищи" in text or 'найди' in text:
                        query = text.replace("поищи", "").replace("найди", "").replace(self.assistant_name, "").strip()
                        approve_folder = self.audio_paths.get('approve_folder')
                        if approve_folder:
                            react(approve_folder)
                        search_yandex(query)

                    elif 'проверь' in text:
                        approve_folder = self.audio_paths.get('approve_folder')
                        if approve_folder:
                            react(approve_folder)
                        search_links()
                    elif 'выключи комп' in text:
                        shutdown_windows()
                    elif "пауз" in text or "вруб" in text:
                        controller.play_pause()
                        approve_folder = self.audio_paths.get('approve_folder')
                        if approve_folder:
                            react(approve_folder)
                    elif "след" in text:
                        controller.next_track()
                        approve_folder = self.audio_paths.get('approve_folder')
                        if approve_folder:
                            react(approve_folder)
                    elif "пред" in text:
                        controller.previous_track()
                        approve_folder = self.audio_paths.get('approve_folder')
                        if approve_folder:
                            react(approve_folder)
                    else:
                        echo_folder = self.audio_paths.get('echo_folder')
                        if echo_folder:
                            react(echo_folder)

                    # Проверка, была ли вызвана реакция
                    if reaction_triggered:
                        what_folder = self.audio_paths.get('what_folder')
                        if what_folder:
                            react(what_folder)

                elif "перезагрузка ассистент" in text:
                    restart_system()
                    break
        except Exception as e:
            logger.error(f"Ошибка в основном цикле ассистента: {e}")
            logger.error(traceback.format_exc())

    def get_audio(self):
        """Преобразование речи с микрофона в текст."""
        model_path = os.path.join(get_base_directory(), "model_ru")  # Используем правильный путь к модели
        logger.info(f"Используется модель по пути: {model_path}")  # Логируем путь к модели

        try:
            # Преобразуем путь в UTF-8
            model_path_utf8 = model_path.encode("utf-8").decode("utf-8")
            # Пытаемся загрузить модель
            model = Model(model_path_utf8)
            logger.info("Модель успешно загружена.")  # Логируем успешную загрузку модели
        except Exception as e:
            # Логируем полный стек вызовов при ошибке
            logger.error(f"Ошибка при загрузке модели: {e}. Возможно путь содержит кириллицу.")
            return
        rec_ru = KaldiRecognizer(model, 16000)
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=512)
            stream.start_stream()
            while self.is_assistant_running:
                try:
                    data = stream.read(256, exception_on_overflow=False)
                    if len(data) == 0:
                        break

                    if rec_ru.AcceptWaveform(data):
                        result = rec_ru.Result()
                        result = result[14:-3]  # Обрезаем результат для получения только текста
                        if result:
                            logger.info(f"Распознанный текст: {result}")  # Логируем распознанный текст
                        yield result.lower()  # Возвращаем результат с помощью yield
                except Exception as e:
                    logger.error(f"Ошибка при обработке аудиоданных: {e}")  # Логируем ошибку обработки данных
                    logger.error("Подробная информация об ошибке:")
                    logger.error(traceback.format_exc())  # Выводим полный стек вызовов
                    break

        except Exception as e:
            logger.error(f"Ошибка при работе с аудиопотоком: {e}")  # Логируем ошибку работы с потоком
            logger.error("Подробная информация об ошибке:")
            logger.error(traceback.format_exc())  # Выводим полный стек вызовов
        finally:
            logger.info("Остановка аудиопотока...")  # Логируем остановку потока
            stream.stop_stream()
            stream.close()
            p.terminate()

    def handle_app_command(self, text, action):
        """Обработка команд для приложений"""
        for keyword, filename in self.commands.items():
            if keyword in text:
                handler_links(filename, action)  # Вызываем обработчик ярлыков
                return True  # Возвращаем True, если команда была успешно обработана
        return False  # Возвращаем False, если команда не была найдена

    def handle_folder_command(self, text, action):
        """Обработка команд для папок"""
        for keyword, folder_path in self.commands.items():
            if keyword in text:
                if folder_path.endswith('.lnk'):
                    return False  # Прекращаем обработку, если это файл приложения
                handler_folder(folder_path, action)  # Вызываем обработчик папок
                return True  # Возвращаем True, если команда была успешно обработана
        return False  # Возвращаем False, если команда не была найдена

    def open_folder(self):
        """Обработка нажатия кнопки 'Открыть папку с ярлыками'"""
        current_directory = get_base_directory()  # Используем функцию для получения базового пути
        folder_path = os.path.join(current_directory, "links for assist")
        self.log_area.append(folder_path)

        # Проверяем, существует ли папка
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            os.startfile(folder_path)  # Открываем папку
        else:
            # Если папка не существует, создаем её
            try:
                os.makedirs(folder_path)  # Создаем папку
                self.log_area.append(f'Папка "{folder_path}" была создана.')
                os.startfile(folder_path)  # Открываем папку после создания
            except Exception as e:
                self.log_area.append(f'Ошибка при создании папки: {e}')

    def check_shortcuts(self):
        """Обработка нажатия кнопки 'Проверка ярлыков'"""
        approve_folder = self.audio_paths.get('approve_folder')
        react(approve_folder)
        search_links()

    def open_settings(self):
        """Обработка нажатия кнопки 'Настройки'"""
        try:
            settings_dialog = SettingsDialog(self.speaker, self.assistant_name, self.steam_path,
                                             self)  # Передаем текущий голос и путь к steam.exe
            settings_dialog.voice_changed.connect(self.update_voice)  # Подключаем сигнал
            settings_dialog.exec_()
        except Exception as e:
            logger.error(f"Ошибка при открытии настроек: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось открыть настройки.")

    def add_new_command(self):
        """Обработка нажатия кнопки 'Новая команда'"""
        settings_dialog = AppCommandWindow(self)
        settings_dialog.exec_()

    def added_commands(self):
        """Обработка нажатия кнопки 'Добавленные команды'"""
        commands_window = AddedCommandsWindow(self)  # Передаем ссылку на родительский класс
        commands_window.exec_()  # Открываем диалоговое окно

    def add_folder_command(self):
        """Обработка нажатия кнопки 'Добавить команду для папки'"""
        folder_dialog = AddFolderCommand(self)
        folder_dialog.exec_()

    def update_voice(self, new_voice):
        """Обновление голоса и путей к аудиофайлам"""
        self.speaker = new_voice
        self.audio_paths = get_audio_paths(self.speaker)  # Обновляем пути к аудиофайлам
        logger.info(f"Голос изменен на: {new_voice}")

    def clear_logs(self):
        """Очистка файла логов и текстового поля"""
        log_file_path = os.path.join(get_base_directory(), 'assistant.log')  # Используем правильный путь к логам
        try:
            with open(log_file_path, 'w', encoding='utf-8') as file:
                file.write("")  # Записываем пустую строку
            self.log_area.clear()
            self.log_area.append("Логи очищены.")
            self.last_position = 0  # Сбрасываем позицию последнего прочитанного байта
        except Exception as e:
            self.log_area.append(f"Ошибка при очистке логов: {e}")

    def toggle_autostart(self):
        """Включение или отключение автозапуска"""
        if self.autostart_checkbox.isChecked():
            self.add_to_autostart()
        else:
            self.remove_from_autostart()

    def add_to_autostart(self):
        """Добавление программы в автозапуск через планировщик задач"""
        current_directory = get_base_directory()
        write_directory = os.path.dirname(current_directory)
        # Путь к исполняемому файлу и .bat файлу
        exe_path = os.path.join(write_directory, 'Assistant.exe')  # Замените на имя вашего исполняемого файла
        bat_path = os.path.join(write_directory, 'start_assistant.bat')
        task_name = "VirtualAssistant"  # Имя задачи в планировщике

        # Определяем, запущена ли программа как исполняемый файл или как скрипт
        if getattr(sys, 'frozen', False):
            # Если программа запущена как исполняемый файл
            target_path = exe_path
        else:
            # Если программа запущена как скрипт, создаем .bat файл
            if not os.path.isfile(bat_path):
                try:
                    with open(bat_path, 'w', encoding='utf-8') as bat_file:
                        bat_file.write(f'@echo off\npython "{os.path.abspath(__file__)}"')
                    self.log_area.append(f"Создан .bat файл: {bat_path}")
                except Exception as e:
                    self.log_area.append(f"Ошибка при создании .bat файла: {e}")
                    return
            target_path = bat_path
        logger.info(f"Создан следующий путь для планировщика: {target_path}")
        # Проверка наличия файла
        if not os.path.isfile(target_path):
            logger.info(f"Ошибка: Файл '{target_path}' не найден.")
            return

        # Команда для создания задачи в планировщике
        command = [
            'schtasks',
            '/create',
            '/tn', task_name,
            '/tr', f"'{target_path}'",  # Используем путь к найденному файлу
            '/sc', 'onlogon',
            '/rl', 'highest',
            '/f'
        ]
        try:
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            # Декодируем вывод с использованием правильной кодировки (например, cp866)
            output = result.stdout.decode('cp866')
            self.log_area.append("Программа добавлена в автозапуск.")
            self.log_area.append(output)  # Вывод результата
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode('cp866')  # Декодируем ошибку
            self.log_area.append(f"Ошибка при добавлении в автозапуск: {error_output}")

    def remove_from_autostart(self):
        """Удаление программы из автозапуска через планировщик задач"""
        task_name = "VirtualAssistant"  # Имя задачи в планировщике
        # Команда для удаления задачи из планировщика
        command = [
            'schtasks',
            '/delete',
            '/tn', task_name,
            '/f'
        ]
        try:
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            output = result.stdout.decode('cp866')  # Декодируем вывод
            self.log_area.append("Программа удалена из автозапуска.")
            self.log_area.append(output)  # Вывод результата
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode('cp866')  # Декодируем ошибку
            self.log_area.append(f"Ошибка при удалении из автозапуска: {error_output}")

    def check_autostart(self):
        """Проверка, добавлена ли программа в автозапуск"""
        task_name = "VirtualAssistant"
        command = ['schtasks', '/query', '/tn', task_name]

        try:
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            output = result.stdout.decode('cp866')  # Декодируем вывод
            self.autostart_checkbox.setChecked(True)
            self.log_area.append("Задача найдена: " + output)
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode('cp866')  # Декодируем ошибку
            self.autostart_checkbox.setChecked(False)
            self.log_area.append("Задача не найдена.")
            self.log_area.append(error_output)


class SettingsDialog(QDialog):
    voice_changed = pyqtSignal(str)  # Сигнал для передачи нового голоса

    def __init__(self, current_voice: str, current_name: str, current_steam_path: str, parent):
        """
        Конструктор диалога настроек.
        :param current_voice: Текущий выбранный голос.
        :param current_name: Текущее имя ассистента.
        :param current_steam_path: Текущий путь к steam.exe.
        :param parent: Родительский виджет.
        """
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setFixedSize(300, 400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Поле для ввода имени ассистента
        name_label = QLabel("Имя ассистента:", self)
        main_layout.addWidget(name_label, alignment=Qt.AlignLeft)

        self.name_input = QLineEdit(self)
        self.name_input.setText(current_name)  # Устанавливаем текущее имя
        main_layout.addWidget(self.name_input)

        label = QLabel("Выберите голос:", self)
        main_layout.addWidget(label, alignment=Qt.AlignLeft)

        # Создаем выпадающий список с вариантами голосов
        self.voice_combo = QComboBox(self)
        self.voice_combo.addItems(list(speakers.keys()))  # Добавляем ключи в QComboBox
        main_layout.addWidget(self.voice_combo)

        # Устанавливаем текущий голос (значение)
        self.current_voice = current_voice  # Текущий установленный голос (значение)

        # Устанавливаем текущий индекс в QComboBox на основе значения
        current_key = next(key for key, value in speakers.items() if value == self.current_voice)
        self.voice_combo.setCurrentText(current_key)

        # Подключаем сигнал изменения выбора
        self.voice_combo.currentIndexChanged.connect(self.on_voice_change)

        # Поле для выбора пути к steam.exe
        self.steam_label = QLabel("Укажите полный путь к файлу steam.exe", self)
        main_layout.addWidget(self.steam_label, alignment=Qt.AlignLeft)

        self.steam_path_input = QLineEdit(self)
        self.steam_path_input.setText(current_steam_path)  # Устанавливаем текущий путь
        main_layout.addWidget(self.steam_path_input)

        # Кнопка для выбора файла steam.exe
        select_steam_button = QPushButton("Выбрать файл", self)
        select_steam_button.clicked.connect(self.select_steam_file)
        main_layout.addWidget(select_steam_button)

        main_layout.addStretch()

        # Кнопка для закрытия настроек
        close_button = QPushButton("Применить", self)
        close_button.clicked.connect(self.apply_settings)
        main_layout.addWidget(close_button)
        main_layout.setAlignment(close_button, Qt.AlignBottom)

    def select_steam_file(self):
        """Открывает диалог для выбора файла steam.exe."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, "Выберите steam.exe",
                                                       "", "Executable Files (*.exe);;All Files (*)")
            if file_path:  # Проверяем, что файл был выбран
                self.steam_path_input.setText(file_path)  # Устанавливаем выбранный путь в QLineEdit
        except Exception as e:
            logger.error(f"Ошибка при выборе файла steam.exe: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось выбрать файл: {e}")

    def on_voice_change(self, index):
        """Обработка изменения голоса."""
        new_voice_key = self.voice_combo.itemText(index)  # Получаем выбранный ключ
        if new_voice_key not in speakers:
            logger.error(f"Ключ голоса '{new_voice_key}' не найден в списке speakers.")
            return

        new_voice_value = speakers[new_voice_key]  # Извлекаем значение по ключу

        # Обновляем текущий голос (значение)
        if new_voice_value != self.current_voice:
            self.current_voice = new_voice_value  # Обновляем текущий голос (значение)
            self.voice_changed.emit(new_voice_value)  # Отправляем сигнал с новым значением
            logger.info(f"Выбранный голос: {new_voice_key}")

    def apply_settings(self):
        """Применить настройки и сохранить их."""
        new_assistant_name = self.name_input.text().strip().lower()  # Убираем лишние пробелы
        if not new_assistant_name:
            QMessageBox.warning(self, "Ошибка", "Имя ассистента не может быть пустым.")
            return

        new_steam_path = self.steam_path_input.text().strip()  # Убираем лишние пробелы

        # Проверяем, существует ли файл steam.exe
        if not os.path.isfile(new_steam_path):
            QMessageBox.warning(self, "Ошибка", f"Файл '{new_steam_path}' не найден.\n Укажите путь к файлу steam.exe")
            return

        changes_made = False  # Флаг, указывающий на изменения

        # Проверяем, изменилось ли имя ассистента
        if new_assistant_name != self.parent().assistant_name:
            self.parent().assistant_name = new_assistant_name  # Сохраняем новое имя в родительском классе
            changes_made = True

        # Проверяем, изменился ли голос
        if self.current_voice != self.parent().speaker:
            self.parent().speaker = self.current_voice  # Обновляем голос в родительском классе
            changes_made = True

        # Проверяем, изменился ли путь к steam.exe
        if new_steam_path != self.parent().steam_path:
            self.parent().steam_path = new_steam_path  # Обновляем путь к steam.exe в родительском классе
            changes_made = True

        # Если были изменения, сохраняем настройки и показываем сообщение
        if changes_made:
            self.parent().save_settings()  # Сохраняем настройки
            QMessageBox.information(self, "Внимание", "Настройки применены")
            logger.info("Настройки успешно применены.")

        self.close()


class AppCommandWindow(QDialog):
    """
    Обработка создания окна для добавления новых команд
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        self.base_path = get_base_directory()
        self.commands = self.load_commands(os.path.join(self.base_path, 'commands.json'))
        self.load_shortcuts()  # Загружаем ярлыки при инициализации
        self.setFixedSize(350, 300)
        self.setWindowIcon(QIcon(os.path.join(self.base_path, 'assist-min.ico')))

    def init_ui(self):
        self.setWindowTitle("Добавить команду")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Поле для ввода ключа
        self.key_input = QLineEdit(self)
        self.key_input.setPlaceholderText("Команда (уникальное слово)")
        layout.addWidget(QLabel("Команда (Слово, на которое будет реагировать):"))
        layout.addWidget(self.key_input)

        # Поле для выбора имени ярлыка
        self.shortcut_combo = QComboBox(self)
        layout.addWidget(QLabel("Выберите ярлык:"))
        layout.addWidget(self.shortcut_combo)

        layout.addStretch()

        # Кнопка применения
        self.apply_button = QPushButton("Применить", self)
        self.apply_button.clicked.connect(self.apply_command)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def load_commands(self, filename):
        """Загружает команды из JSON-файла."""
        file_path = os.path.join(self.base_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.error(f"Файл {filename} не найден по пути: {file_path}")
            QMessageBox.critical(self, "Ошибка", f"Файл {filename} не найден.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл {filename} содержит некорректный JSON.")
            QMessageBox.critical(self, "Ошибка", "Ошибка в формате файла JSON.")
            return {}

    def save_commands(self, filename):
        """Сохраняет команды в JSON-файл."""
        file_path = os.path.join(self.base_path, filename)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(self.commands, file, ensure_ascii=False, indent=4)
            logger.info("Команда обновлена в файле.")

    def load_shortcuts(self):
        """Загружает имена ярлыков из файла links.json."""
        links_file = os.path.join(self.base_path, 'links.json')
        try:
            with open(links_file, 'r', encoding='utf-8') as file:
                links = json.load(file)
                shortcut_names = list(links.keys())  # Получаем только имена ярлыков
                self.shortcut_combo.addItems(shortcut_names)  # Добавляем имена ярлыков в комбобокс
        except FileNotFoundError:
            logger.error(f"Файл {links_file} не найден.")
            QMessageBox.critical(self, "Ошибка", f"Файл {links_file} не найден.")
        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл {links_file} содержит некорректный JSON.")
            QMessageBox.critical(self, "Ошибка", "Ошибка в формате файла JSON.")

    def apply_command(self):
        """Добавляет новую команду в JSON-файл."""
        key = self.key_input.text().lower()
        selected_shortcut_name = self.shortcut_combo.currentText()

        try:
            # Проверка на существование ключа
            if key in self.commands:
                QMessageBox.warning(self, "Предупреждение", f"Команда '{key}' уже существует.")
                return

            # Добавляем новую команду в словарь commands
            self.commands[key] = selected_shortcut_name
            # Сохраняем обновленный словарь в JSON-файл
            self.save_commands('commands.json')

            QMessageBox.information(self, "Внимание",
                                    f"Команда '{key}' успешно добавлена.\nНеобходим перезапуск программы.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            logger.error(f"Ошибка: {e}")


class AddedCommandsWindow(QDialog):
    """
        Класс для обработки окна "Добавленные функции"
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent  # Сохраняем ссылку на родительский класс
        self.base_path = get_base_directory()
        self.commands = self.parent.commands  # Доступ к командам родителя
        self.init_ui()
        self.update_commands_list()  # Обновляем список команд при инициализации

    def init_ui(self):
        self.setWindowTitle("Добавленные команды")
        self.setFixedSize(500, 500)

        layout = QVBoxLayout(self)

        self.commands_list = QListWidget(self)
        layout.addWidget(self.commands_list)

        # Кнопка "Удалить"
        self.delete_button = QPushButton("Удалить выбранную команду", self)
        self.delete_button.clicked.connect(self.delete_command)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def load_commands_from_file(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.warning(f"Файл {filename} не найден. Создаём новый файл.")
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump({}, file)  # Создаём пустой JSON
            return {}
        except json.JSONDecodeError:
            logger.error("Ошибка: файл содержит некорректный JSON.")
            QMessageBox.critical(self, "Ошибка", "Ошибка в формате файла JSON.")
            return {}

    def update_commands_list(self):
        """Обновляет список команд в QListWidget, загружая их из файла."""
        self.commands_list.clear()  # Очищаем текущий список
        # Загружаем команды из файла
        commands_file = os.path.join(self.base_path, 'commands.json')  # Полный путь к файлу
        self.commands = self.load_commands_from_file(commands_file)

        if not isinstance(self.commands, dict):
            logger.error("Файл JSON не содержит словарь.")
            QMessageBox.critical(self, "Ошибка", "Файл JSON имеет некорректный формат.")
            self.commands = {}  # Сбрасываем команды

        for key, value in self.commands.items():
            # Создаем строку для отображения в QListWidget
            item_text = f"{key} : {value}"  # Теперь value - это просто строка
            try:
                item = QListWidgetItem(item_text)  # Создаем элемент
                self.commands_list.addItem(item)  # Добавляем элемент в QListWidget
            except Exception as e:
                logger.error(f"Ошибка при добавлении элемента: {e}")

    def delete_command(self):
        """Удаляет команду по выбранному ключу."""
        selected_items = self.commands_list.selectedItems()  # Получаем выбранные элементы

        if not selected_items:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите команду для удаления.")
            return  # Если ничего не выбрано, выходим

        for item in selected_items:
            key = item.text().split(" : ")[0]  # Получаем ключ команды из текста элемента

            if key in self.commands:
                del self.commands[key]  # Удаляем команду из словаря
                self.commands_list.takeItem(self.commands_list.row(item))  # Удаляем элемент из QListWidget

        self.save_commands()  # Сохраняем изменения в файл

    def save_commands(self):
        """Сохраняет команды в файл commands.json."""
        commands_file = os.path.join(self.base_path, 'commands.json')  # Полный путь к файлу
        try:
            with open(commands_file, 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=4)
                logger.info("Список команд обновлён.")
        except IOError as e:
            logger.error(f"Ошибка записи в файл {commands_file}: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить команды.")


class AddFolderCommand(QDialog):
    """
        Класс для обработки окна "Добавить команду для папки"
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        self.base_path = get_base_directory()
        self.commands = self.load_commands(os.path.join(self.base_path, 'commands.json'))
        self.setFixedSize(350, 250)
        self.setWindowIcon(QIcon(os.path.join(self.base_path, 'assist-min.ico')))

    def init_ui(self):
        """
            инициализация
        """
        self.setWindowTitle("Добавить команду")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Поле для ввода ключа
        self.key_input = QLineEdit(self)
        self.key_input.setPlaceholderText("Команда (уникальное слово)")
        layout.addWidget(QLabel("Команда (Слово, на которое будет реагировать):"))
        layout.addWidget(self.key_input)

        # Поле для выбора имени ярлыка
        self.folder_path = QLineEdit(self)
        layout.addWidget(QLabel("Выберите папку:"))
        layout.addWidget(self.folder_path)

        # Кнопка для выбора папки
        select_steam_button = QPushButton("Обзор...", self)
        select_steam_button.clicked.connect(self.select_folder)
        layout.addWidget(select_steam_button)

        layout.addStretch()

        # Кнопка применения
        self.apply_button = QPushButton("Применить", self)
        self.apply_button.clicked.connect(self.apply_command)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def select_folder(self):
        # Открываем диалог выбора папки
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку", "")
        if folder:
            self.folder_path.setText(folder)
        else:
            logger.info("Выбор папки отменен.")

    def load_commands(self, filename):
        """Загружает команды из JSON-файла."""
        file_path = os.path.join(self.base_path, filename)
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            else:
                logger.warning(f"Файл {filename} не найден. Будет создан новый.")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при чтении файла {filename}: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка в формате файла JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Ошибка при загрузке команд: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке команд: {e}")
            return {}

    def save_commands(self, filename):
        """Сохраняет команды в JSON-файл."""
        file_path = os.path.join(self.base_path, filename)
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=4)
                logger.info("Команда обновлена в файле.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении команд: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении команд: {e}")

    def apply_command(self):
        """Добавляет новую команду в JSON-файл."""
        key = self.key_input.text().strip().lower()
        selected_folder_path = self.folder_path.text().strip()

        if not key or not selected_folder_path:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, заполните все поля.")
            return

        try:
            # Проверка на существование ключа
            if key in self.commands:
                QMessageBox.warning(self, "Предупреждение", f"Команда '{key}' уже существует.")
                return

            # Добавляем новую команду в словарь commands
            self.commands[key] = selected_folder_path
            # Сохраняем обновленный словарь в JSON-файл
            self.save_commands('commands.json')

            QMessageBox.information(self, "Внимание",
                                    f"Команда '{key}' успешно добавлена.\nНеобходим перезапуск программы.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            logger.error(f"Ошибка: {e}")


class ColorSettingsWindow(QDialog):
    """
    Класс обрабатывающий окно изменения оформления интерфейса
    (изменение цветовой палитры, сохранение и выбор пресетов)
    """
    colorChanged = pyqtSignal()  # Определяем сигнал

    def get_base_directory(self):
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

    def __init__(self, current_styles, color_setting_path, parent=None):
        super().__init__(parent)
        self.styles = current_styles  # Передаем текущие стили
        self.color_settings_path = color_setting_path
        self.init_ui()
        self.load_color_settings()  # Загружаем текущие цвета

    def init_ui(self):
        self.setWindowTitle('Настройка цветов интерфейса')
        self.setFixedSize(300, 400)

        # Инициализация переменных для цветов
        self.bg_color = ""
        self.btn_color = ""
        self.text_color = ""
        self.text_edit_color = ""

        # Кнопки для выбора цветов
        self.bg_button = QPushButton('Выберите цвет фона')
        self.bg_button.clicked.connect(self.choose_background_color)

        self.btn_button = QPushButton('Выберите цвет кнопок')
        self.btn_button.clicked.connect(self.choose_button_color)

        self.text_button = QPushButton('Выберите цвет текста')
        self.text_button.clicked.connect(self.choose_text_color)

        self.text_edit_button = QPushButton('Выберите цвет текста в логах')
        self.text_edit_button.clicked.connect(self.choose_text_edit_color)

        # Кнопка для применения изменений
        self.apply_button = QPushButton('Применить')
        self.apply_button.clicked.connect(self.apply_changes)

        # Кнопка для сохранения пресета
        self.save_preset_button = QPushButton('Сохранить пресет')
        self.save_preset_button.clicked.connect(self.save_preset)

        # Выпадающий список для выбора существующих пресетов
        self.preset_combo_box = QComboBox()
        self.load_presets()  # Загружаем существующие пресеты
        self.preset_combo_box.setCurrentIndex(0)
        self.preset_combo_box.currentIndexChanged.connect(self.load_preset)

        # Размещение элементов
        layout = QVBoxLayout()
        layout.addWidget(self.bg_button)
        layout.addWidget(self.btn_button)
        layout.addWidget(self.text_button)
        layout.addWidget(self.text_edit_button)
        layout.addWidget(self.save_preset_button)
        layout.addWidget(QLabel('Пресеты:'))
        layout.addWidget(self.preset_combo_box)
        layout.addStretch()
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def load_color_settings(self):
        """Загружает текущие цвета из переданных стилей."""
        self.bg_color = self.styles.get("QWidget", {}).get("background-color", "#2E3440")
        self.btn_color = self.styles.get("QPushButton", {}).get("background-color", "#3858c7")
        self.text_color = self.styles.get("QWidget", {}).get("color", "#8eaee5")
        self.text_edit_color = self.styles.get("QTextEdit", {}).get("background-color", "#2E3440")

    def choose_background_color(self):
        color = QColorDialog.getColor(Qt.white, self)
        if color.isValid():
            self.bg_color = color.name()

    def choose_button_color(self):
        color = QColorDialog.getColor(Qt.white, self)
        if color.isValid():
            self.btn_color = color.name()

    def choose_text_color(self):
        color = QColorDialog.getColor(Qt.white, self)
        if color.isValid():
            self.text_color = color.name()

    def choose_text_edit_color(self):
        color = QColorDialog.getColor(Qt.white, self)
        if color.isValid():
            self.text_edit_color = color.name()

    def apply_changes(self):
        try:
            new_styles = {
                "QWidget": {
                    "background-color": self.bg_color,
                    "color": self.text_edit_color,
                    "font-size": "13px"
                },
                "QPushButton": {
                    "background-color": self.btn_color,
                    "color": self.text_edit_color,
                    "height": "25px",
                    "border": f"1px solid {self.btn_color}",
                    "font-size": "13px"
                },
                "QPushButton:hover": {
                    "background-color": self.darken_color(self.btn_color, 10),
                    "color": self.text_edit_color,
                    "font-size": "13px"
                },
                "QPushButton:pressed": {
                    "background-color": self.darken_color(self.btn_color, 30),
                    "padding-left": "3px",
                    "padding-top": "3px",
                },
                "QTextEdit": {
                    "background-color": self.bg_color,
                    "color": self.text_color,
                    "border": "1px solid",
                    "border-radius": "4px",
                    "font-size": "12px"
                },
                "label_version": {
                    "color": self.text_color,
                    "font-size": "10px"
                },
                "label_message": {
                    "color": self.text_edit_color,
                    "font-size": "13px"
                }
            }

            self.save_color_settings(new_styles)  # Сохранение в файл
            self.colorChanged.emit()  # Излучаем сигнал о изменении цвета
        except Exception as e:
            logger.info(f"Ошибка при применении изменений: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось применить изменения: {e}")

    def save_color_settings(self, new_styles):
        """Сохраняет новые стили в color_settings.json."""
        with open(self.color_settings_path, 'w') as json_file:
            json.dump(new_styles, json_file, indent=4)

    def save_preset(self):
        """Сохраняет текущие стили как новый пресет."""
        preset_name, ok = QInputDialog.getText(self, 'Сохранить пресет', 'Введите имя пресета:')
        if ok and preset_name:
            preset_path = os.path.join(self.get_base_directory(), 'presets', f'{preset_name}.json')
            new_styles = {
                "QWidget": {
                    "background-color": self.bg_color,
                    "color": self.text_color,
                    "font-size": "13px"
                },
                "QPushButton": {
                    "background-color": self.btn_color,
                    "color": self.text_color,
                    "height": "25px",
                    "border": f"1px solid {self.btn_color}",
                    "font-size": "13px"
                },
                "QPushButton:hover": {
                    "background-color": self.darken_color(self.btn_color, 10),
                    "color": self.text_color,
                    "font-size": "13px"
                },
                "QPushButton:pressed": {
                    "background-color": self.darken_color(self.btn_color, 30),
                    "padding-left": "3px",
                    "padding-top": "3px",
                },
                "QTextEdit": {
                    "background-color": self.bg_color,
                    "color": self.text_edit_color,
                    "border": "1px solid",
                    "border-radius": "4px",
                    "font-size": "12px"
                },
                "label_version": {
                    "color": self.text_edit_color,
                    "font-size": "10px"
                },
                "label_message": {
                    "color": self.text_color,
                    "font-size": "13px"
                }
            }
            with open(preset_path, 'w') as json_file:
                json.dump(new_styles, json_file, indent=4)
            self.load_presets()  # Обновляем список пресетов

    def load_presets(self):
        """Загружает существующие пресеты в выпадающий список."""
        self.preset_combo_box.clear()
        self.preset_combo_box.addItem("Выбрать пресет")

        # Получаем базовую директорию
        base_dir = self.get_base_directory()
        presets_dir = os.path.join(base_dir, 'presets')  # Объединяем базовую директорию с папкой presets

        # Проверяем, существует ли директория, если нет - создаем
        if not os.path.exists(presets_dir):
            os.makedirs(presets_dir)

        # Загружаем все файлы .json из директории пресетов
        for filename in os.listdir(presets_dir):
            if filename.endswith('.json'):
                self.preset_combo_box.addItem(filename[:-5])  # Добавляем имя файла без .json

    def load_preset(self):
        """Загружает выбранный пресет из файла."""
        selected_preset = self.preset_combo_box.currentText()
        if selected_preset and selected_preset != "Выбрать пресет":
            # Получаем базовую директорию
            base_dir = self.get_base_directory()
            preset_path = os.path.join(base_dir, 'presets', f'{selected_preset}.json')
            try:
                with open(preset_path, 'r') as json_file:
                    styles = json.load(json_file)
                    # Загружаем цвета для основных элементов
                    self.bg_color = styles.get("QWidget", {}).get("background-color", "#2E3440")
                    self.btn_color = styles.get("QPushButton", {}).get("background-color", "#3858c7")
                    self.text_color = styles.get("QWidget", {}).get("color", "#ffffff")
                    self.text_edit_color = styles.get("QTextEdit", {}).get("color", "#2E3440")

                    # Загружаем цвета для меток
                    label_version_color = styles.get("label_version", {}).get("color", self.text_edit_color)
                    label_message_color = styles.get("label_message", {}).get("color", self.text_color)

                    # Обновляем переменные для меток
                    self.text_color = label_version_color  # Используем цвет из label_version
                    self.text_edit_color = label_message_color  # Используем цвет из label_message

                    logger.info("Пресет успешно загружен.")
            except FileNotFoundError:
                logger.error(f"Файл пресета '{preset_path}' не найден.")
            except json.JSONDecodeError:
                logger.error(f"Ошибка: файл пресета '{preset_path}' содержит некорректный JSON.")
            except Exception as e:
                logger.error(f"Ошибка при загрузке пресета: {e}")

    def darken_color(self, color_str, amount):
        """Уменьшает яркость цвета на заданное количество (в формате hex)."""
        color = QColor(color_str)
        color.setRed(max(0, color.red() - amount))
        color.setGreen(max(0, color.green() - amount))
        color.setBlue(max(0, color.blue() - amount))
        return color.name()


# Запуск приложения
if __name__ == '__main__':
    app = QApplication([])
    window = Assistant()
    app.exec_()
