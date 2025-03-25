"""
Этот модуль представляет собой основной файл для работы ассистента.

Здесь реализованы функции и классы, необходимые для
запуска и управления ассистентом, включая обработку
пользовательского ввода и управление интерфейсом.
"""
import csv
import json
import logging
import os.path
import random
import tempfile
from datetime import timedelta
from pathlib import Path
import sys
import time
import traceback
import zipfile
import requests
from packaging import version
import psutil
import winsound
import pandas as pd
from func_list import search_links, handler_links, handler_folder
from function_list_main import *
import simpleaudio as sa
import numpy as np
import threading
import pyaudio
import subprocess
from script_audio import controller
from speak_functions import react, react_detail
from logging_config import logger
from lists import get_audio_paths
from vosk import Model, KaldiRecognizer
from PyQt5.QtGui import QIcon, QColor, QCursor
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, \
                             QPushButton, QCheckBox, QSystemTrayIcon, QAction, qApp, QMenu, QMessageBox, \
                             QTextEdit, QDialog, QLabel, QComboBox, QLineEdit, QListWidget, QListWidgetItem, \
                             QFileDialog, QColorDialog, QSlider, QInputDialog, QStackedWidget, QFrame)
from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer, QEvent, pyqtSignal, QSettings


speakers = dict(Пласид='placide', Бестия='rogue', Джонни='johnny', СанСаныч='sanych',
                Санбой='sanboy', Тигрица='tigress', Стейтем='stathem')

# Сырая ссылка на version.txt в GitHub
VERSION_FILE_URL = "https://raw.githubusercontent.com/AndreyDanilov1999/oldAssistant_v2/refs/heads/master/version.txt"
CHANGELOG_FILE_URL = "https://raw.githubusercontent.com/AndreyDanilov1999/oldAssistant_v2/refs/heads/master/changelog.txt"



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

    def check_memory_usage(self, limit_mb):
        """
        Проверка потребления оперативной памяти
        :param limit_mb:
        :return:
        """
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # В МБ
        if memory_usage > limit_mb:
            logger.error(f"Превышен лимит памяти: {memory_usage} МБ > {limit_mb} МБ")
            return False
        return True

    def __init__(self):
        super().__init__()
        self.latest_version_url = None
        self.relax_button = None
        self.open_folder_button = None
        self.autostart_checkbox = None
        self.tray_icon = None
        self.start_button = None
        self.styles = None
        self.changelog_file_path = None
        self.log_file_path = os.path.join(self.get_base_directory(), 'assistant.log')
        self.init_logger()
        self.settings_file_path = os.path.join(self.get_base_directory(), 'user_settings', 'settings.json')
        self.update_settings(self.settings_file_path)
        self.settings = self.load_settings()
        self.color_settings_path = os.path.join(self.get_base_directory(), 'user_settings', 'color_settings.json')
        self.commands = self.load_commands(os.path.join(self.get_base_directory(), 'user_settings', 'commands.json'))
        self.default_preset_style = os.path.join(self.get_base_directory(), 'user_settings', 'presets', 'default.json')
        self.process_names = os.path.join(self.get_base_directory(), 'user_settings', 'process_names.json')
        self.last_position = 0
        self.steam_path = self.settings.get('steam_path', '')  # значение по умолчанию, если ключ отсутствует
        self.volume_assist = self.settings.get('volume_assist', 0.2)  # значение по умолчанию, если ключ отсутствует
        self.is_assistant_running = False
        self.show_upd_msg = self.settings.get("show_upd_msg", False)  # Значение по умолчанию: False
        self.assistant_thread = None
        self.is_censored = self.settings.get('is_censored', False)  # значение по умолчанию, если ключ отсутствует
        self.censored_thread = None
        self.speaker = self.settings.get("voice", "johnny")
        self.assistant_name = self.settings.get('assistant_name', "джо")
        self.assist_name2 = self.settings.get('assist_name2', "джо")
        self.assist_name3 = self.settings.get('assist_name3', "джо")
        self.audio_paths = get_audio_paths(self.speaker)
        self.MEMORY_LIMIT_MB = 1024
        self.version = "1.2.6"
        self.ps = "Powered by theoldman"
        self.label_version = QLabel(f"Версия: {self.version} {self.ps}", self)
        self.label_message = QLabel('', self)
        self.initui()
        self.check_or_create_folder()
        self.load_and_apply_styles()
        self.apply_styles()
        # Проверка автозапуска при старте программы
        self.check_autostart()
        self.hide()
        self.run_assist()
        self.check_update_label()
        self.check_for_updates_app()

    def initui(self):
        """Инициализация пользовательского интерфейса."""
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # Инициализируем QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(os.path.join(self.get_base_directory(), 'icon_assist.ico')))

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
        self.open_folder_button = QPushButton("Ваши ярлыки")
        self.open_folder_button.clicked.connect(self.open_folder)
        left_layout.addWidget(self.open_folder_button)

        # Кнопка "Настройки"
        self.settings_button = QPushButton("Настройки")
        self.settings_button.clicked.connect(self.open_settings)
        left_layout.addWidget(self.settings_button)

        # Кнопка "Оформление интерфейса"
        self.style_settings_button = QPushButton('Оформление')
        self.style_settings_button.clicked.connect(self.open_color_settings)
        left_layout.addWidget(self.style_settings_button)

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

        # Кнопка "Процессы ярлыков"
        self.link_process_button = QPushButton("Процессы ярлыков")
        self.link_process_button.clicked.connect(self.link_process)
        left_layout.addWidget(self.link_process_button)

        # Кнопка "Релакс?"
        self.relax_button = QPushButton("Релакс?")
        self.relax_button.clicked.connect(self.relax_window)
        left_layout.addWidget(self.relax_button)

        # Кнопка "Прочее"
        self.other_button = QPushButton("Прочее")
        self.other_button.clicked.connect(self.other_options)
        left_layout.addWidget(self.other_button)

        # Добавляем растяжку, чтобы кнопки были вверху
        left_layout.addStretch()

        # Текст "Доступна новая версия"
        self.update_label = QLabel("")
        self.update_label.setCursor(QCursor(Qt.PointingHandCursor))  # Курсор в виде руки
        self.update_label.mousePressEvent = self.open_download_link  # Обработка клика
        left_layout.addWidget(self.update_label)

        self.update_button = QPushButton("Установить обновление")
        self.update_button.clicked.connect(self.update_app)
        left_layout.addWidget(self.update_button)

        # Лейбл, при нажатии будет открываться changelog
        self.label_version.setCursor(QCursor(Qt.PointingHandCursor))
        self.label_version.mousePressEvent = self.changelog_window
        left_layout.addWidget(self.label_version)

        # Правая часть (поле для логов)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        # Кнопка "Очистить логи"
        self.clear_logs_button = QPushButton("Очистить логи")
        self.clear_logs_button.clicked.connect(self.clear_logs)

        right_layout.addWidget(self.log_area)
        right_layout.addWidget(self.clear_logs_button)

        # Добавляем левую и правую части в основной макет
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)

        # Устанавливаем основной макет для окна
        self.setLayout(main_layout)

        # Настройки окна
        self.setWindowTitle("Виртуальный помощник")
        self.setGeometry(500, 250, 900, 600)

        # Установка иконки для окна
        self.setWindowIcon(QIcon(os.path.join(self.get_base_directory(), 'icon_assist.ico')))

        # Инициализация FileSystemWatcher
        self.init_file_watcher()

        # Загрузка предыдущих записей из файла логов
        self.load_existing_logs()

        # Таймер для периодической проверки файла
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(1000)  # Проверка каждую секунду

    def open_download_link(self, event):
        """Открывает ссылку на скачивание при клике на текст."""
        if self.update_label.text() == "Установлена последняя версия":
            audio_paths = self.audio_paths
            update_button = audio_paths.get('update_button')
            react_detail(update_button)
        else:
            # Проверяем, есть ли ссылка
            if self.latest_version_url:
                webbrowser.open(self.latest_version_url)

    def check_update_label(self):
        """
        Метод для отображения или скрытия кнопки "Установить обновление"
        """
        # Проверяем текст лейбла и управляем видимостью кнопки
        if self.update_label.text() == "Доступна новая версия":
            self.update_button.show()
        else:
            self.update_button.hide()

    def check_for_updates_app(self):
        """Проверяет обновления, загружая данные из сырых URL-ссылок"""
        try:
            # Загружаем файл с версией с таймаутом 10 секунд
            version_response = requests.get(
                VERSION_FILE_URL,
                timeout=10,
                headers={'Cache-Control': 'no-cache'}
            )
            version_response.raise_for_status()

            # Загружаем changelog с таймаутом 15 секунд (может быть больше)
            changelog_response = requests.get(
                CHANGELOG_FILE_URL,
                timeout=15,
                headers={'Cache-Control': 'no-cache'}
            )
            changelog_response.raise_for_status()

            # Обрабатываем файл версии
            version_content = version_response.text.strip()
            self.logger.info(f"Получена информация о версии: {version_content}")

            # Сохраняем changelog во временный файл
            changelog_path = os.path.join(tempfile.gettempdir(), 'changelog.txt')
            with open(changelog_path, 'w', encoding='utf-8') as f:
                f.write(changelog_response.text)

            # Обновляем путь к changelog
            self.changelog_file_path = changelog_path

            # Парсим данные версии
            version_parts = version_content.split(maxsplit=1)
            if len(version_parts) < 2:
                raise ValueError("Файл версии должен содержать номер версии и URL через пробел")

            latest_version, latest_version_url = version_parts[0], version_parts[1].strip()

            # Валидация версии
            current_ver = version.parse(self.version)
            latest_ver = version.parse(latest_version)

            # Сохраняем ссылку для использования в show_popup
            self.latest_version_url = latest_version_url

            # Проверяем обновление
            if latest_ver > current_ver:
                self.update_label.setText("Доступна новая версия")
                self.check_update_label()

                if self.settings.get("show_upd_msg", True):
                    self.show_popup(latest_version)
            else:
                self.update_label.setText("Установлена последняя версия")

        except requests.Timeout:
            self.logger.warning("Таймаут при проверке обновлений")
            self.update_label.setText("Ошибка соединения")
            self.update_label.setStyleSheet("color: orange;")

        except requests.RequestException as e:
            self.logger.error(f"Ошибка сети: {str(e)}")
            self.update_label.setText("Нет соединения")
            self.update_label.setStyleSheet("color: orange;")

        except ValueError as e:
            self.logger.error(f"Ошибка формата данных: {str(e)}")
            self.update_label.setText("Ошибка данных")
            self.update_label.setStyleSheet("color: red;")

        except Exception as e:
            self.logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
            self.update_label.setText("Ошибка обновления")
            self.update_label.setStyleSheet("color: red;")

    def show_popup(self, latest_version):
        """Показывает всплывающее окно обновления, которое не закрывается при просмотре изменений"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Доступно обновление")
        msg_box.setIcon(QMessageBox.Information)

        # Основной текст
        msg_box.setText(
            f"<b>Доступна новая версия: {latest_version}</b>"
            "<p>Хотите скачать обновление?</p>"
        )

        # Кастомная кнопка для изменений
        changes_btn = msg_box.addButton("Список изменений", QMessageBox.ActionRole)
        changes_btn.setIcon(QIcon.fromTheme("text-x-generic"))

        # Стандартные кнопки
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.button(QMessageBox.Yes).setText("Установить")
        msg_box.button(QMessageBox.No).setText("Позже")

        # Чекбокс
        checkbox = QCheckBox("Больше не показывать")
        msg_box.setCheckBox(checkbox)

        # Стилизация
        for btn in [changes_btn, msg_box.button(QMessageBox.Yes), msg_box.button(QMessageBox.No)]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 5px 15px;
                    min-width: 120px;
                }
            """)

        # Модифицированная обработка
        while True:
            response = msg_box.exec_()

            # Если нажали "Список изменений"
            if msg_box.clickedButton() == changes_btn:
                self.changelog_window(None)  # Показываем changelog
                continue  # Продолжаем показ основного окна

            # Если нажали другую кнопку
            if response == QMessageBox.Yes:
                webbrowser.open(self.latest_version_url)

            # Сохранение настроек
            if checkbox.isChecked():
                self.show_upd_msg = False
                self.save_settings()

            break  # Выходим из цикла

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

    def check_or_create_folder(self):
        folder_path = os.path.join(get_base_directory(), 'user_settings', "links for assist")
        self.log_area.append(folder_path)

        # Проверяем, существует ли папка
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            pass
        else:
            # Если папка не существует, создаем её
            try:
                os.makedirs(folder_path)  # Создаем папку
                self.log_area.append('Папка "links for assist" была создана.')
            except Exception as e:
                self.log_area.append(f'Ошибка при создании папки: {e}')

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

        if 'update_label' in self.styles:
            self.update_label.setStyleSheet(self.format_style(self.styles['update_label']))

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
        """Загружает настройки из settings.json."""
        try:
            with open(self.settings_file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}  # Если файл не найден или повреждён, возвращаем пустой словарь

    def save_settings(self):
        """Сохраняет настройки в файл settings.json."""
        settings_data = {
            "voice": self.speaker,
            "assistant_name": self.assistant_name,
            "assist_name2": self.assist_name2,
            "assist_name3": self.assist_name3,
            "steam_path": self.steam_path,
            "is_censored": self.is_censored,
            "volume_assist": self.volume_assist,
            "show_upd_msg": self.show_upd_msg
        }
        try:
            # Проверяем, существует ли папка user_settings
            os.makedirs(os.path.dirname(self.settings_file_path), exist_ok=True)

            # Сохраняем настройки в файл
            with open(self.settings_file_path, 'w', encoding='utf-8') as file:
                json.dump(settings_data, file, ensure_ascii=False, indent=4)

            logger.info("Настройки сохранены.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {e}")
            raise  # Повторно выбрасываем исключение, если нужно

    def update_settings(self, settings_file, default_settings=None):
        """
        Проверяет файл настроек на наличие ключей из default_settings.
        Если ключ отсутствует, добавляет его со значением по умолчанию.
        """
        if default_settings is None:
            default_settings = {
                "voice": "johnny",
                "assistant_name": "джо",
                "assist_name2": "джо",
                "assist_name3": "джо",
                "steam_path": "D:/Steam/steam.exe",
                "is_censored": True,
                "volume_assist": 0.2,
                "show_upd_msg": True
            }

        # Загружаем текущие настройки
        if os.path.exists(settings_file):
            with open(settings_file, "r", encoding="utf-8") as file:
                try:
                    settings = json.load(file)
                except json.JSONDecodeError:
                    settings = {}
        else:
            settings = {}

        # Обновляем настройки, если ключи отсутствуют
        updated = False
        for key, value in default_settings.items():
            if key not in settings:
                settings[key] = value
                updated = True

        # Сохраняем обновленные настройки, если они изменились
        if updated:
            with open(settings_file, "w", encoding="utf-8") as file:
                json.dump(settings, file, ensure_ascii=False, indent=4)

        return settings

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
            logger.info("Ошибка: не найден аудиофайл.")

        # Остановка ассистента
        if self.assistant_thread and self.assistant_thread.is_alive():
            self.assistant_thread.join()  # Ожидание завершения потока

    def censor_counter(self):
        # Путь к CSV-файлу
        CSV_FILE = os.path.join(self.get_base_directory(), 'user_settings', 'censor_counter.csv')

        # Создаем файл, если он не существует
        if not Path(CSV_FILE).exists():
            with open(CSV_FILE, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['date', 'score', 'total_score'])  # Заголовки столбцов

        # Получаем текущую дату
        today = datetime.now().strftime('%Y-%m-%d')

        # Читаем данные из CSV
        rows = []
        with open(CSV_FILE, mode='r') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Пропускаем заголовки
            for row in reader:
                # Пропускаем пустые строки
                if not row:
                    continue
                # Проверяем, что строка содержит достаточно данных
                if len(row) >= 3:
                    rows.append(row)

        # Ищем запись для текущей даты
        found = False
        total_score = 0
        for row in rows:
            try:
                # Преобразуем score и total_score в int
                row[1] = int(row[1])
                row[2] = int(row[2])
                total_score += row[1]  # Считаем общее количество

                if row[0] == today:
                    # Если запись найдена, увеличиваем score на 1
                    row[1] += 1
                    row[2] += 1
                    found = True
            except (ValueError, IndexError) as e:
                print(f"Ошибка при обработке строки {row}: {e}")
                continue

        # Если запись не найдена, добавляем новую
        if not found:
            rows.append([today, 1, total_score + 1])

        # Записываем обновленные данные обратно в CSV
        with open(CSV_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)  # Записываем заголовки
            writer.writerows(rows)  # Записываем данные

# "Основной цикл ассистента"
# "--------------------------------------------------------------------------------------------------"
# "Основной цикл ассистента"

    def run_script(self):
        """Основной цикл ассистента"""
        greeting()
        last_unrecognized_command = None  # Хранит контекст неудачной команды
        last_activity_time = time.time()  # Время последней активности

        if not self.initialize_audio():
            return

        try:
            for text in self.get_audio():
                current_time = time.time()

                # Сбрасываем контекст, если прошло более 7 секунд без активности
                if last_unrecognized_command and (current_time - last_activity_time) > 7:
                    last_unrecognized_command = None
                    logger.info("Сброс контекста из-за неактивности (7 секунд)")
                    continue

                if not self.is_assistant_running:
                    break

                # Обновляем время последней активности при получении текста
                last_activity_time = current_time

                # Проверка памяти и цензуры (без изменений)
                if not self.check_memory_usage(self.MEMORY_LIMIT_MB):
                    logger.error("Превышен лимит памяти. Завершение работы.")
                    break

                if any(keyword in text for keyword in ['сук', 'суч', 'пизд', 'еба', 'ёба',
                                                       'нах', 'ху', 'бля', 'ебу', 'еп',
                                                       'ёп', 'гандон', 'пид']):
                    self.censor_counter()

                if self.is_censored and any(keyword in text for keyword in ['сук', 'суч', 'пизд', 'еба', 'ёба',
                                                                            'нах', 'ху', 'бля', 'ебу', 'еп',
                                                                            'ёп', 'гандон', 'пид']):
                    censored_folder = self.audio_paths.get('censored_folder')
                    react(censored_folder)
                    continue

                # Режим уточнения команды (если предыдущая попытка не удалась)
                if last_unrecognized_command:
                    if text:
                        # Обновляем время последней активности при обработке команды
                        last_activity_time = current_time
                        # Проверяем, содержит ли текст только кириллические символы (исключаем английскую речь)
                        if any(cyr_char in text.lower() for cyr_char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
                            # Сначала проверяем специальные команды (калькулятор, диспетчер и т.д.)
                            special_commands = {
                                'микшер': (open_volume_mixer, close_volume_mixer),
                                'калькул': (open_calc, close_calc),
                                'pain': (open_paint, close_paint),
                                'пэйнт': (open_paint, close_paint),
                                'переменные': (open_path, None),
                                'диспетчер': (open_taskmgr, close_taskmgr)
                            }

                            # Ищем совпадение со специальными командами
                            matched_special = next((kw for kw in special_commands if kw in text.lower()), None)

                            if matched_special:
                                if last_unrecognized_command['action_type'] == 'open':
                                    special_commands[matched_special][0]()
                                elif last_unrecognized_command['action_type'] == 'close':
                                    if special_commands[matched_special][1]:
                                        special_commands[matched_special][1]()
                                last_unrecognized_command = None
                                continue

                            # Ищем прямое совпадение с командами из файла
                            matched_keyword = next((kw for kw in self.commands if kw in text.lower()), None)

                            if matched_keyword:
                                # Восстанавливаем полную команду
                                restored_command = f"{last_unrecognized_command['action']} {matched_keyword}"
                                logger.info(f"Восстановленная команда: {restored_command}")

                                # Определяем тип действия
                                action_type = last_unrecognized_command['action_type']

                                # Пытаемся обработать как приложение
                                app_processed = self.handle_app_command(restored_command, action_type)

                                # Если не получилось, пробуем как папку
                                if not app_processed:
                                    folder_processed = self.handle_folder_command(restored_command, action_type)

                                    if not folder_processed:
                                        logger.warning(f"Не удалось обработать команду: {restored_command}")
                                        what_folder = self.audio_paths.get('what_folder')
                                        if what_folder:
                                            react(what_folder)
                                        continue

                                last_unrecognized_command = None

                if self.assistant_name in text or self.assist_name2 in text or self.assist_name3 in text:
                    reaction_triggered = False
                    action_keywords = ['откр', 'закр', 'вкл', 'выкл', 'запус',
                                       'отруб', 'выруб']
                    action = next((kw for kw in action_keywords if kw in text), None)

                    commands = []
                    if " и " in text:
                        commands = text.split(" и ")
                    elif " а также " in text:
                        commands = text.split(" а также ")
                    elif " потом " in text:
                        commands = text.split(" потом ")
                    elif " ещё " in text:
                        commands = text.split(" ещё ")
                    else:
                        commands = [text]

                    for command in commands:
                        command = command.strip()

                        if action and not any(kw in command for kw in action_keywords):
                            command = f"{action} {command}"

                        # Системные команды (без изменений)
                        if 'выключи комп' in command:
                            shutdown_windows()
                            continue
                        elif 'перезагрузить комп' in command:
                            restart_windows()
                            continue

                        # Определяем тип действия
                        action_type = None
                        if any(kw in command for kw in ['запус', 'откр', 'вкл', 'вруб']):
                            action_type = 'open'
                        elif any(kw in command for kw in ['закр', 'выкл', 'выруб', 'отруб']):
                            action_type = 'close'

                        if action_type:
                            if "микшер" in command:
                                if action_type == 'open':
                                    open_volume_mixer()
                                else:
                                    close_volume_mixer()
                            elif 'калькул' in command:
                                if action_type == 'open':
                                    open_calc()
                                else:
                                    close_calc()
                            elif 'pain' in command or 'пэйнт' in command or 'prin' in command:
                                if action_type == 'open':
                                    open_paint()
                                else:
                                    close_paint()
                            elif 'переменные' in command:
                                if action_type == 'open':
                                    open_path()
                            elif 'диспетчер' in command:
                                if action_type == 'open':
                                    open_taskmgr()
                                else:
                                    close_taskmgr()
                            else:
                                # Пытаемся обработать команду
                                app_processed = self.handle_app_command(command, action_type)
                                folder_processed = not app_processed and self.handle_folder_command(command, action_type)

                                if not app_processed and not folder_processed:
                                    # Сохраняем контекст для уточнения
                                    last_unrecognized_command = {
                                        'action': action,
                                        'action_type': action_type,
                                        'original_text': text
                                    }
                                    reaction_triggered = True
                        else:
                            # Поиск и другие команды (без изменений)
                            if "поищи" in command or 'найди' in command:
                                query = (command.replace("поищи", "").replace("найди", "")
                                         .replace(self.assistant_name, "")
                                         .replace(self.assist_name2, "")
                                         .replace("в интернете", "")
                                         .replace("в инете", "")
                                         .replace(self.assist_name3, "").strip())
                                approve_folder = self.audio_paths.get('approve_folder')
                                if approve_folder:
                                    react(approve_folder)
                                search_yandex(query)
                            else:
                                echo_folder = self.audio_paths.get('echo_folder')
                                if echo_folder:
                                    react(echo_folder)

                    if reaction_triggered:
                        what_folder = self.audio_paths.get('what_folder')
                        if what_folder:
                            react(what_folder)
                        if self.speaker == "sanboy" and random.random() <= 0.7:
                            prorok_sanboy = self.audio_paths.get('prorok_sanboy')
                            react_detail(prorok_sanboy)

                # Обработка плеера (без изменений)
                if 'плеер' in text:
                    if any(keyword in text for keyword in
                           ['пауз', 'пуск', 'пуст', 'вкл', 'вруб', 'отруб', 'выкл', 'стоп']):
                        controller.play_pause()
                        player_folder = self.audio_paths.get('player_folder')
                        react(player_folder)
                    elif any(keyword in text for keyword in ['след', 'впер', 'дальш', 'перекл']):
                        controller.next_track()
                        player_folder = self.audio_paths.get('player_folder')
                        react(player_folder)
                    elif any(keyword in text for keyword in ['пред', 'назад']):
                        controller.previous_track()
                        player_folder = self.audio_paths.get('player_folder')
                        react(player_folder)

        except Exception as e:
            logger.error(f"Ошибка в основном цикле ассистента: {e}")
            logger.error(traceback.format_exc())
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText(f"Ошибка в основном цикле ассистента: {e}")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()

    # "Основной цикл ассистента(конец)"
    # "--------------------------------------------------------------------------------------------------"
    # "Основной цикл ассистента(конец)"

    def check_microphone_available(self):
        """Проверка наличия микрофона в системе."""
        p = pyaudio.PyAudio()
        try:
            # Получаем информацию об устройстве ввода по умолчанию
            default_input_device = p.get_default_input_device_info()
            logger.info(f"Устройство ввода: {default_input_device.get('name')}")
            return True
        except IOError:
            # Если устройство по умолчанию не найдено
            logger.warning("Микрофон не обнаружен.")
            return False
        finally:
            p.terminate()

    def initialize_audio(self):
        """Инициализация моделей и аудиопотока."""
        # Проверка наличия микрофона
        if not self.check_microphone_available():
            QMessageBox.warning(self, "Ошибка",
                                "Микрофон не обнаружен. Пожалуйста, подключите микрофон и перезагрузите программу.")
            return False

        model_path_ru = os.path.join(get_base_directory(), "model_ru")
        model_path_en = os.path.join(get_base_directory(), "model_en")
        logger.info(f"Используются модели:  ru - {model_path_ru}; en - {model_path_en}")

        try:
            # Преобразуем путь в UTF-8
            model_path_ru_utf8 = model_path_ru.encode("utf-8").decode("utf-8")
            model_path_en_utf8 = model_path_en.encode("utf-8").decode("utf-8")

            # Пытаемся загрузить модель
            self.model_ru = Model(model_path_ru_utf8)
            self.model_en = Model(model_path_en_utf8)
            logger.info("Модели успешно загружены.")  # Логируем успешную загрузку модели
        except Exception as e:
            # Логируем полный стек вызовов при ошибке
            logger.error(f"Ошибка при загрузке модели: {e}. Возможно путь содержит кириллицу.")
            return False

        # Инициализация распознавателей
        self.rec_ru = KaldiRecognizer(self.model_ru, 16000)
        self.rec_en = KaldiRecognizer(self.model_en, 16000)

        # Инициализация аудиопотока
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=512)
        self.stream.start_stream()

        return True

    def get_audio(self):
        """Преобразование речи с микрофона в текст."""
        try:
            while self.is_assistant_running:
                data = self.stream.read(1024, exception_on_overflow=False)
                if len(data) == 0:
                    break

                # Сбрасываем промежуточные результаты
                ru_text = ""
                en_text = ""

                # Обрабатываем через русскую модель
                if self.rec_ru.AcceptWaveform(data):
                    result = json.loads(self.rec_ru.Result())
                    ru_text = result.get("text", "").strip().lower()

                # Обрабатываем через английскую модель
                if self.rec_en.AcceptWaveform(data):
                    result = json.loads(self.rec_en.Result())
                    temp_en = result.get("text", "").strip().lower()
                    if temp_en and temp_en != "huh":
                        en_text = temp_en

                # Определяем приоритетный результат
                final_text = ""
                if ru_text:  # Русский текст имеет высший приоритет
                    final_text = ru_text
                    logger.info(f"Распознано (RU): {ru_text}")
                elif en_text:  # Если русского нет, используем английский
                    final_text = en_text
                    logger.info(f"Распознано (EN): {en_text}")

                if final_text:
                    yield final_text

        except Exception as e:
            error_file = self.audio_paths.get('error_file')
            react_detail(error_file)
            logger.error(f"Ошибка при обработке аудиоданных: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.info("Остановка аудиопотока...")
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

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
                if folder_path.endswith('.lnk') or folder_path.endswith('.url'):
                    return False  # Прекращаем обработку, если это файл приложения
                handler_folder(folder_path, action)  # Вызываем обработчик папок
                return True  # Возвращаем True, если команда была успешно обработана
        return False  # Возвращаем False, если команда не была найдена

    def open_folder(self):
        """Обработка нажатия кнопки 'Открыть папку с ярлыками'"""
        current_directory = get_base_directory()  # Используем функцию для получения базового пути
        folder_path = os.path.join(current_directory, 'user_settings', "links for assist")
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

    def open_settings(self):
        """Обработка нажатия кнопки 'Настройки'"""
        try:
            settings_dialog = SettingsDialog(self.speaker, self.assistant_name, self.assist_name2,
                                             self.assist_name3, self.steam_path, self.volume_assist,
                                             self)  # Передаем текущий голос и путь к steam.exe
            settings_dialog.voice_changed.connect(self.update_voice)  # Подключаем сигнал
            settings_dialog.exec_()
        except Exception as e:
            logger.error(f"Ошибка при открытии настроек: {e}")
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText(f"Ошибка при открытии настроек: {e}")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()

    def add_new_command(self):
        """Обработка нажатия кнопки 'Новая команда'"""
        settings_dialog = AppCommandWindow(self)
        settings_dialog.exec_()

    def added_commands(self):
        """Обработка нажатия кнопки 'Добавленные команды'"""
        commands_window = AddedCommandsWindow(self)  # Передаем ссылку на родительский класс
        commands_window.exec_()  # Открываем диалоговое окно

    def link_process(self):
        """Обработка нажатия кнопки 'Процессы ярлыков'"""
        link_process_window = LinkProcessWindow(self)
        link_process_window.exec_()

    def add_folder_command(self):
        """Обработка нажатия кнопки 'Добавить команду для папки'"""
        folder_dialog = AddFolderCommand(self)
        folder_dialog.exec_()

    def relax_window(self):
        """Обработка нажатия кнопки Релакс"""
        dialog = RelaxWindow(self)
        dialog.exec_()

    def other_options(self):
        """Открываем окно с настройками"""
        self.other_window = OtherOptionsWindow(self)
        self.other_window.show()

    def changelog_window(self, event):
        """Открываем окно с логами изменений"""
        dialog = ChangelogWindow(self)
        dialog.exec_()

    def update_app(self):
        """Обработка нажатия кнопки Установить обновление"""
        dialog = UpdateApp(self)
        dialog.main()

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
        exe_path = os.path.join(write_directory, 'Assistant.exe')
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
            self.log_area.append(output)
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode('cp866')  # Декодируем ошибку
            self.autostart_checkbox.setChecked(False)
            self.log_area.append("Задача не найдена.")
            self.log_area.append(error_output)


class SettingsDialog(QDialog):
    voice_changed = pyqtSignal(str)  # Сигнал для передачи нового голоса

    def __init__(self, current_voice: str, current_name: str, current_name2: str,
                 current_name3: str, current_steam_path: str, current_volume: int, parent):
        """
        Конструктор диалога настроек.
        :param current_voice: Текущий выбранный голос.
        :param current_name: Текущее имя ассистента.
        :param current_steam_path: Текущий путь к steam.exe.
        :param parent: Родительский виджет.
        """
        super().__init__(parent)
        self.parent = parent
        self.settings = QSettings("MyCompany", "MyApp")  # Инициализация настроек
        self.setWindowTitle("Настройки")
        self.setFixedSize(300, 500)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Поле для ввода имени ассистента
        name_label = QLabel("Основное имя ассистента:", self)
        main_layout.addWidget(name_label, alignment=Qt.AlignLeft)

        self.name_input = QLineEdit(self)
        self.name_input.setText(current_name)  # Устанавливаем текущее имя
        main_layout.addWidget(self.name_input)

        # Поле для ввода имени №2
        name_label = QLabel("Дополнительно:", self)
        main_layout.addWidget(name_label, alignment=Qt.AlignLeft)

        self.name2_input = QLineEdit(self)
        self.name2_input.setText(current_name2)  # Устанавливаем текущее имя
        main_layout.addWidget(self.name2_input)

        # Поле для ввода имени №3
        self.name3_input = QLineEdit(self)
        self.name3_input.setText(current_name3)  # Устанавливаем текущее имя
        main_layout.addWidget(self.name3_input)

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

        self.volume_label = QLabel("Громкость ассистента", self)
        main_layout.addWidget(self.volume_label, alignment=Qt.AlignLeft)

        self.volume = QSlider(Qt.Horizontal, self)
        self.volume.setMinimum(0)  # Минимальное значение
        self.volume.setMaximum(100)  # Максимальное значение
        self.volume.setValue(int(current_volume * 100))
        self.volume.setTickInterval(10)  # Интервал для отметок
        self.volume.setSingleStep(5)  # Шаг при перемещении ползунка

        # Подключение сигнала изменения значения ползунка к слоту
        self.volume.valueChanged.connect(self.update_volume)
        main_layout.addWidget(self.volume)

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

        self.censor_check = QCheckBox("Реагировать на мат")
        self.censor_check.setChecked(self.parent.is_censored)  # Устанавливаем состояние галочки
        self.censor_check.stateChanged.connect(self.toggle_censor)
        main_layout.addWidget(self.censor_check)

        # Чекбокс "Уведомлять о новой версии"
        self.update_check = QCheckBox("Уведомлять о новой версии")
        self.update_check.setChecked(self.parent.show_upd_msg)  # Устанавливаем состояние из JSON
        self.update_check.stateChanged.connect(self.toggle_update)
        main_layout.addWidget(self.update_check)

        main_layout.addStretch()

        # Кнопка для закрытия настроек
        close_button = QPushButton("Применить", self)
        close_button.clicked.connect(self.apply_settings)
        main_layout.addWidget(close_button)
        main_layout.setAlignment(close_button, Qt.AlignBottom)

    def update_volume(self, value):
        normalized_value = value / 100.0  # Нормализация значения от 0 до 1
        self.parent.volume_assist = normalized_value

    def toggle_censor(self):
        """Включение или отключение реакции на мат"""
        self.parent.is_censored = self.censor_check.isChecked()

    def toggle_update(self):
        """Обработка изменения состояния чекбокса."""
        self.parent.show_upd_msg = self.update_check.isChecked()

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

        new_assist_name2 = self.name2_input.text().strip().lower()
        new_assist_name3 = self.name3_input.text().strip().lower()

        new_steam_path = self.steam_path_input.text().strip()  # Убираем лишние пробелы

        # Проверяем, существует ли файл steam.exe
        if not os.path.isfile(new_steam_path):
            QMessageBox.warning(self, "Ошибка", f"Файл '{new_steam_path}' не найден.\n Укажите путь к файлу steam.exe")
            return

        # Проверяем, изменилось ли имя ассистента
        if new_assistant_name != self.parent.assistant_name:
            self.parent.assistant_name = new_assistant_name  # Сохраняем новое имя в родительском классе

        if new_assist_name2 != self.parent.assist_name2:
            self.parent.assist_name2 = new_assist_name2
        if new_assist_name2 == '':
            self.parent.assist_name2 = new_assistant_name

        if new_assist_name3 != self.parent.assist_name3:
            self.parent.assist_name3 = new_assist_name3
        if new_assist_name3 == '':
            self.parent.assist_name3 = new_assistant_name

        # Проверяем, изменился ли голос
        if self.current_voice != self.parent.speaker:
            self.parent.speaker = self.current_voice  # Обновляем голос в родительском классе

        # Проверяем, изменился ли путь к steam.exe
        if new_steam_path != self.parent.steam_path:
            self.parent.steam_path = new_steam_path  # Обновляем путь к steam.exe в родительском классе

        self.parent.save_settings()  # Сохраняем настройки

        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('Информация')
        msg_box.setText('Настройки применены!')
        ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
        ok_button.setStyleSheet("padding: 1px 10px;")
        msg_box.exec_()

        logger.info("Настройки успешно применены.")
        self.close()


class AppCommandWindow(QDialog):
    """
    Обработка создания окна для добавления новых команд
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.get_links()
        self.init_ui()
        self.base_path = get_base_directory()
        self.commands = self.parent.load_commands(os.path.join(self.base_path, 'user_settings', 'commands.json'))
        self.load_shortcuts()  # Загружаем ярлыки при инициализации
        self.setFixedSize(350, 300)
        self.setWindowIcon(QIcon(os.path.join(self.base_path, 'icon_assist.ico')))

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

    def get_links(self):
        search_links()

    def save_commands(self, filename):
        """Сохраняет команды в JSON-файл."""
        file_path = os.path.join(self.base_path, filename)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(self.commands, file, ensure_ascii=False, indent=4)
            logger.info("Команда обновлена в файле.")

    def load_shortcuts(self):
        """Загружает имена ярлыков из файла links.json."""
        links_file = os.path.join(self.base_path, 'user_settings', 'links.json')
        try:
            with open(links_file, 'r', encoding='utf-8') as file:
                links = json.load(file)
                shortcut_names = list(links.keys())  # Получаем только имена ярлыков
                self.shortcut_combo.addItems(shortcut_names)  # Добавляем имена ярлыков в комбобокс
        except FileNotFoundError:
            logger.error(f"Файл {links_file} не найден.")
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText(f"Файл {links_file} не найден.")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()
        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл {links_file} содержит некорректный JSON.")
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText("Ошибка в формате файла JSON.")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()

    def apply_command(self):
        """Добавляет новую команду в JSON-файл."""
        key = self.key_input.text().lower()
        selected_shortcut_name = self.shortcut_combo.currentText()

        try:
            if not key:
                winsound.MessageBeep(winsound.MB_ICONHAND)
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle('Предупреждение')
                msg_box.setText("Команда не указана!")
                ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
                ok_button.setStyleSheet("padding: 1px 10px;")
                msg_box.exec_()
                return
            # Проверка на существование ключа
            if key in self.commands:
                winsound.MessageBeep(winsound.MB_ICONHAND)
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle('Предупреждение')
                msg_box.setText(f"Команда '{key}' уже существует.")
                ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
                ok_button.setStyleSheet("padding: 1px 10px;")
                msg_box.exec_()
                return

            # Добавляем новую команду в словарь commands
            self.commands[key] = selected_shortcut_name
            # Сохраняем обновленный словарь в JSON-файл
            self.save_commands('user_settings/commands.json')
            self.parent.commands = self.parent.load_commands(
                os.path.join(self.base_path, 'user_settings', 'commands.json'))

            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Информация')
            msg_box.setText(f"Команда '{key}' успешно добавлена")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()

        except Exception as e:
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText(str(e))
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()
            logger.error(f"Ошибка: {e}")


class AddedCommandsWindow(QDialog):
    """ Класс для обработки окна "Добавленные функции" """

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
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText("Ошибка в формате файла JSON.")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()
            return {}

    def update_commands_list(self):
        """Обновляет список команд в QListWidget, загружая их из файла."""
        self.commands_list.clear()  # Очищаем текущий список
        # Загружаем команды из файла
        commands_file = os.path.join(self.base_path, 'user_settings', 'commands.json')  # Полный путь к файлу
        self.commands = self.load_commands_from_file(commands_file)

        if not isinstance(self.commands, dict):
            logger.error("Файл JSON не содержит словарь.")
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText("Файл JSON имеет некорректный формат.")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()
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
        """Удаляет команду по выбранному ключу и соответствующий кортеж из process_names.json."""
        selected_items = self.commands_list.selectedItems()  # Получаем выбранные элементы

        if not selected_items:
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Предупреждение')
            msg_box.setText("Пожалуйста, выберите команду для удаления.")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()
            return  # Если ничего не выбрано, выходим

        for item in selected_items:
            key = item.text().split(" : ")[0]  # Получаем ключ команды из текста элемента
            if key in self.commands:
                # Получаем значение (ярлык или путь) удаляемой команды
                value = self.commands[key]
                del self.commands[key]  # Удаляем команду из словаря
                self.commands_list.takeItem(self.commands_list.row(item))  # Удаляем элемент из QListWidget
                # Удаляем соответствующий кортеж из process_names.json
                process_names_file = os.path.join(self.base_path, 'user_settings', 'process_names.json')
                try:
                    with open(process_names_file, 'r', encoding='utf-8') as file:
                        process_names = json.load(file)
                    # Удаляем запись, если её ключ совпадает со значением удаляемой команды
                    updated_process_names = [entry for entry in process_names if list(entry.keys())[0] != value]
                    with open(process_names_file, 'w', encoding='utf-8') as file:
                        json.dump(updated_process_names, file, ensure_ascii=False, indent=4)

                except IOError as e:
                    logger.error(f"Ошибка при работе с файлом {process_names_file}: {e}")
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle('Ошибка')
                    msg_box.setText(f"Не удалось обновить process_names.json: {e}")
                    ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
                    ok_button.setStyleSheet("padding: 1px 10px;")
                    msg_box.exec_()

        self.save_commands()  # Сохраняем изменения в commands.json

    def save_commands(self):
        """Сохраняет команды в файл commands.json."""
        commands_file = os.path.join(self.base_path, 'user_settings', 'commands.json')  # Полный путь к файлу
        try:
            with open(commands_file, 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=4)
                logger.info("Список команд обновлён.")
        except IOError as e:
            logger.error(f"Ошибка записи в файл {commands_file}: {e}")
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText("Не удалось сохранить команды.")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()


class AddFolderCommand(QDialog):
    """
        Класс для обработки окна "Добавить команду для папки"
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        self.base_path = get_base_directory()
        self.commands = self.parent.load_commands(os.path.join(self.base_path, 'user_settings', 'commands.json'))
        self.setFixedSize(350, 250)
        self.setWindowIcon(QIcon(os.path.join(self.base_path, 'icon_assist.ico')))

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

    def save_commands(self, filename):
        """Сохраняет команды в JSON-файл."""
        file_path = os.path.join(self.base_path, filename)
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=4)
                logger.info("Команда обновлена в файле.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении команд: {e}")
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText(f"Ошибка при сохранении команд: {e}")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()

    def apply_command(self):
        """Добавляет новую команду в JSON-файл."""
        key = self.key_input.text().strip().lower()
        selected_folder_path = self.folder_path.text().strip()

        if not key or not selected_folder_path:
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText("Пожалуйста, заполните все поля.")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()
            return

        try:
            # Проверка на существование ключа
            if key in self.commands:
                winsound.MessageBeep(winsound.MB_ICONHAND)
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle('Предупреждение')
                msg_box.setText(f"Команда '{key}' уже существует.")
                ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
                ok_button.setStyleSheet("padding: 1px 10px;")
                msg_box.exec_()
                return

            # Добавляем новую команду в словарь commands
            self.commands[key] = selected_folder_path
            # Сохраняем обновленный словарь в JSON-файл
            self.save_commands('user_settings/commands.json')
            self.parent.commands = self.parent.load_commands(
                os.path.join(self.base_path, 'user_settings', 'commands.json'))

            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Информация')
            msg_box.setText(f"Команда '{key}' успешно добавлена")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()

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
        # Инициализация переменных для цветов
        self.bg_color = ""
        self.btn_color = ""
        self.text_color = ""
        self.text_edit_color = ""
        self.border_color = ""
        self.load_color_settings()  # Загружаем текущие цвета

    def init_ui(self):
        self.setWindowTitle('Настройка цветов интерфейса')
        self.setFixedSize(300, 400)

        # Кнопки для выбора цветов
        self.bg_button = QPushButton('Выберите цвет фона')
        self.bg_button.clicked.connect(self.choose_background_color)

        self.btn_button = QPushButton('Выберите цвет кнопок')
        self.btn_button.clicked.connect(self.choose_button_color)

        self.border_button = QPushButton('Выберите цвет обводки')
        self.border_button.clicked.connect(self.choose_border_color)

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
        layout.addWidget(self.border_button)
        layout.addWidget(self.text_button)
        layout.addWidget(self.text_edit_button)
        layout.addWidget(self.save_preset_button)
        layout.addWidget(QLabel('Пресеты:'))
        layout.addWidget(self.preset_combo_box)
        layout.addStretch()
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def load_color_settings(self):
        """Загружает текущие цвета из файла настроек."""
        self.bg_color = self.styles.get("QWidget", {}).get("background-color", "#1d2028")
        self.btn_color = self.styles.get("QPushButton", {}).get("background-color", "#293f85")
        self.text_color = self.styles.get("QPushButton", {}).get("color", "#8eaee5")
        self.text_edit_color = self.styles.get("QTextEdit", {}).get("color", "#ffffff")
        self.border_color = self.styles.get("QPushButton", {}).get("border", "1px solid #293f85")

    def choose_background_color(self):
        try:
            initial_color = QColor(self.bg_color) if hasattr(self, 'bg_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.bg_color = color.name()
        except Exception as e:
            logger.error(e)

    def choose_button_color(self):
        try:
            initial_color = QColor(self.btn_color) if hasattr(self, 'btn_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.btn_color = color.name()
        except Exception as e:
            logger.error(e)

    def choose_border_color(self):
        try:
            initial_color = QColor(self.border_color) if hasattr(self, 'border_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.border_color = color.name()
        except Exception as e:
            logger.error(e)

    def choose_text_color(self):
        try:
            initial_color = QColor(self.text_color) if hasattr(self, 'text_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.text_color = color.name()
        except Exception as e:
            logger.error(e)

    def choose_text_edit_color(self):
        try:
            initial_color = QColor(self.text_edit_color) if hasattr(self, 'text_edit_color') else Qt.white
            color = QColorDialog.getColor(initial_color, self)
            if color.isValid():
                self.text_edit_color = color.name()
        except Exception as e:
            logger.error(e)

    def apply_changes(self):
        try:
            new_styles = {
                "QWidget": {
                    "background-color": self.bg_color,
                    "color": self.text_color,
                    "font-size": "13px"
                },
                "QPushButton": {
                    "background-color": self.btn_color,
                    "color": self.text_color,
                    "height": "30px",
                    "border": f"1px solid {self.border_color}",
                    "border-radius": "3px",
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
                },
                "update_label": {
                    "color": self.text_edit_color,
                    "font-size": "12px"
                }
            }
            self.save_color_settings(new_styles)  # Сохранение в файл
            self.colorChanged.emit()  # Излучаем сигнал об изменении цвета
        except Exception as e:
            logger.info(f"Ошибка при применении изменений: {e}")
            winsound.MessageBeep(winsound.MB_ICONHAND)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Ошибка')
            msg_box.setText(f"Не удалось применить изменения: {e}")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            msg_box.exec_()

    def save_color_settings(self, new_styles):
        """Сохраняет новые стили в color_settings.json."""
        with open(self.color_settings_path, 'w') as json_file:
            json.dump(new_styles, json_file, indent=4)

    def save_preset(self):
        """Сохраняет текущие стили как новый пресет."""
        dialog = CustomInputDialog('Сохранить пресет', 'Введите имя пресета:', self)
        result = dialog.exec_()  # Ждем, пока диалог закроется

        if result == QDialog.Accepted:  # Если нажали "Сохранить"
            preset_name = dialog.get_text()
            if not preset_name:
                winsound.MessageBeep(winsound.MB_ICONHAND)
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle('Ошибка')
                msg_box.setText("Имя пресета не может быть пустым.")
                ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
                ok_button.setStyleSheet("padding: 1px 10px;")
                msg_box.exec_()
                return

            preset_path = os.path.join(self.get_base_directory(), 'user_settings', 'presets', f'{preset_name}.json')
            new_styles = {
                "QWidget": {
                    "background-color": self.bg_color,
                    "color": self.text_edit_color,
                    "font-size": "13px"
                },
                "QPushButton": {
                    "background-color": self.btn_color,
                    "color": self.text_edit_color,
                    "height": "30px",
                    "border": f"1px solid {self.border_color}",
                    "border-radius": "3px",
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
                },
                "update_label": {
                    "color": self.text_color,
                    "font-size": "12px"
                }
            }
            try:
                with open(preset_path, 'w') as json_file:
                    json.dump(new_styles, json_file, indent=4)
                self.load_presets()  # Обновляем список пресетов
            except Exception as e:
                winsound.MessageBeep(winsound.MB_ICONHAND)
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle('Ошибка')
                msg_box.setText(f"Не удалось сохранить пресет: {e}")
                ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
                ok_button.setStyleSheet("padding: 1px 10px;")
                msg_box.exec_()
        else:  # Если нажали "Закрыть" или закрыли диалог
            logger.info("Пресет не сохранен")
            return

    def load_presets(self):
        """Загружает существующие пресеты в выпадающий список."""
        self.preset_combo_box.clear()
        self.preset_combo_box.addItem("Выбрать пресет")

        # Получаем базовую директорию
        base_dir = self.get_base_directory()
        presets_dir = os.path.join(base_dir, 'user_settings',
                                   'presets')  # Объединяем базовую директорию с папкой presets

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
            preset_path = os.path.join(base_dir, 'user_settings', 'presets', f'{selected_preset}.json')
            try:
                with open(preset_path, 'r') as json_file:
                    styles = json.load(json_file)
                    # Загружаем цвета для основных элементов
                    self.bg_color = styles.get("QWidget", {}).get("background-color", "#1d2028")
                    self.btn_color = styles.get("QPushButton", {}).get("background-color", "#293f85")
                    self.text_color = styles.get("QPushButton", {}).get("color", "#8eaee5")
                    self.text_edit_color = styles.get("QTextEdit", {}).get("color", "#ffffff")
                    self.border_color = styles.get("QPushButton", {}).get("border", "1px solid #293f85").split()[
                        -1]  # Извлекаем цвет из border

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


class RelaxWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 30
        self.rate = 60
        self.volume_factor = 0.5
        self.is_playing = False  # Переменная состояния
        self.play_obj = None  # Для хранения ссылки на объект воспроизведения
        self.timer = QTimer(self)  # Создаем таймер

        self.timer.timeout.connect(self.timer_finished)  # Подключаем сигнал таймера к методу

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Релакс?')
        self.setFixedSize(300, 400)

        # Поля для настройки выходного звука
        self.duration_title = QLabel('Укажите длительность в секундах')
        self.duration_field = QLineEdit('30')

        self.rate_title = QLabel('Укажите частоту (не рекомендую выше 450)')
        self.rate_field = QLineEdit('60')

        self.apply_button = QPushButton('Запустить')
        self.apply_button.clicked.connect(self.toggle_play)

        # Создание QLabel для отображения значения
        self.label = QLabel('Значение: 0.50', self)

        # Создание горизонтального ползунка
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setMinimum(0)  # Минимальное значение
        self.slider.setMaximum(100)  # Максимальное значение
        self.slider.setValue(50)  # Начальное значение
        self.slider.setTickInterval(10)  # Интервал для отметок
        self.slider.setSingleStep(1)  # Шаг при перемещении ползунка

        # Подключение сигнала изменения значения ползунка к слоту
        self.slider.valueChanged.connect(self.update_volume)

        # Создание вертикального layout
        layout = QVBoxLayout()
        layout.addWidget(self.duration_title)
        layout.addWidget(self.duration_field)
        layout.addWidget(self.rate_title)
        layout.addWidget(self.rate_field)
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addStretch()
        layout.addWidget(self.apply_button)

        # Установка layout для виджета
        self.setLayout(layout)

    def update_volume(self, value):
        # Обновление текста в QLabel
        normalized_value = value / 100.0  # Нормализация значения от 0 до 1
        self.volume_factor = normalized_value
        self.label.setText(f'Значение: {normalized_value:.2f}')

    def toggle_play(self):
        # Считываем значения длительности и частоты
        try:
            self.duration = int(self.duration_field.text())
            self.label.setText(f'Длительность: {self.duration} секунд')
        except ValueError:
            self.label.setText('Введите корректное значение для длительности')
            return  # Выход, если значение некорректно

        try:
            self.rate = int(self.rate_field.text())
            self.label.setText(f'Частота: {self.rate} Гц')
        except ValueError:
            self.label.setText('Введите корректное значение для частоты')
            return  # Выход, если значение некорректно

        if self.is_playing:
            self.stop_sound()
        else:
            self.generate_sound()
            self.apply_button.setText('Стоп')
            self.timer.start(self.duration * 1000)  # Запускаем таймер на длительность в миллисекундах
            self.is_playing = True  # Устанавливаем состояние воспроизведения

    def stop_sound(self):
        if self.play_obj is not None:
            self.play_obj.stop()  # Остановка воспроизведения
        self.apply_button.setText('Запустить')
        self.timer.stop()  # Останавливаем таймер
        self.is_playing = False  # Устанавливаем состояние не воспроизведения

    def timer_finished(self):
        self.stop_sound()  # Останавливаем звук, когда таймер истекает

    def generate_sound(self):
        sample_rate = 48000
        new_frequency = self.rate
        volume_factor = self.volume_factor

        # Создаем временной массив
        t = np.linspace(0, self.duration, int(sample_rate * self.duration), endpoint=False)
        audio_data = np.sin(2 * np.pi * new_frequency * t)
        audio_data = (audio_data * volume_factor * 32767).astype(np.int16)

        # Воспроизведение аудио
        self.play_obj = sa.play_buffer(audio_data, 1, 2, sample_rate)


class CustomInputDialog(QDialog):
    def __init__(self, title, label, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(300, 100)

        # Поле для ввода текста
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText(label)

        # Кнопки "ОК" и "Отмена"
        self.ok_button = QPushButton('Сохранить', self)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton('Закрыть', self)
        self.cancel_button.clicked.connect(self.reject)  # Закрываем диалог

        # Размещение элементов
        layout = QVBoxLayout()
        layout.addWidget(self.input_field)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_text(self):
        """Возвращает введенный текст."""
        return self.input_field.text().strip()

    def closeEvent(self, event):
        """Обрабатывает событие закрытия окна (крестик)."""
        try:
            self.reject()  # Закрываем диалог
            event.accept()  # Подтверждаем закрытие окна
        except Exception as e:
            logger.error(f"Ошибка при закрытии диалога: {e}")  # Логируем ошибку


class UpdateApp(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Путь к текущей версии программы (на один уровень выше _internal)
        self.CURRENT_DIR = self.get_base_directory()

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

        # Поднимаемся на один уровень выше, если текущая папка - _internal
        if os.path.basename(base_path) == "_internal":
            base_path = os.path.dirname(base_path)
        return base_path

    def select_new_version_archive(self):
        """Выбор ZIP-архива с новой версией программы"""
        archive_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите архив с новой версией программы",
            "",
            "ZIP Files (*.zip)"
        )
        if archive_path and self.validate_new_version_archive(archive_path):
            return archive_path
        return None

    def validate_new_version_archive(self, archive_path):
        """Проверка, что в архиве есть _internal и Assistant.exe"""
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()

            # Проверка наличия папки _internal
            has_internal = any(file.startswith("_internal/") for file in file_list)
            if not has_internal:
                QMessageBox.warning(self, "Ошибка", "В выбранном архиве отсутствует папка _internal.")
                return False

            # Проверка наличия Assistant.exe
            has_assistant_exe = "Assistant.exe" in file_list
            if not has_assistant_exe:
                QMessageBox.warning(self, "Ошибка", "В выбранном архиве отсутствует файл Assistant.exe.")
                return False

            return True
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось проверить архив: {str(e)}")
            return False

    def extract_archive(self, archive_path, extract_dir):
        """Распаковка архива с обработкой кодировки имён файлов"""
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    # Исправляем имя файла
                    try:
                        # Пробуем декодировать имя файла из cp437 (или другой кодировки)
                        file_info.filename = file_info.filename.encode('cp437').decode('utf-8')
                    except UnicodeDecodeError:
                        # Если cp437 не подходит, пробуем другую кодировку (например, cp866)
                        file_info.filename = file_info.filename.encode('cp437').decode('cp866')

                    # Распаковываем файл с исправленным именем
                    zip_ref.extract(file_info, extract_dir)
            return True
        except Exception as e:
            logger.error(f"Не удалось распаковать архив: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось распаковать архив: {str(e)}")
            return False

    def create_scheduler_task(self, archive_path, new_version_dir):
        """Создание задачи в планировщике для обновления"""
        # Команда для выполнения обновления
        correct_archive_path = os.path.normpath(archive_path)
        update_script = f"""
@echo off
timeout /t 5 /nobreak >nul

:: Удаляем все файлы и папки в старой папке, кроме user_settings
for /d %%i in ("{self.CURRENT_DIR}\\*") do (
    if not "%%~nxi"=="_internal" (
        rmdir /s /q "%%i"
    )
)
for %%i in ("{self.CURRENT_DIR}\\*.*") do (
    if not "%%~nxi"=="update.bat" (
        del /q "%%i"
    )
)

:: Удаляем содержимое папки _internal, кроме user_settings
for /d %%i in ("{self.CURRENT_DIR}\\_internal\\*") do (
    if not "%%~nxi"=="user_settings" (
        rmdir /s /q "%%i"
    )
)
for %%i in ("{self.CURRENT_DIR}\\_internal\\*.*") do (
    if not "%%~nxi"=="update.bat" (
        del /q "%%i"
    )
)

set "exclude_folder=_internal\\user_settings"

:: Создаем временный файл exclude.txt
echo %exclude_folder% > exclude.txt

:: Копируем файлы из новой папки в старую, исключая user_settings
xcopy "{new_version_dir.replace(os.sep, '/')}" "{self.CURRENT_DIR.replace(os.sep, '/')}" /E /I /H /-Y /EXCLUDE:exclude.txt

:: Удаляем временный файл exclude.txt
del exclude.txt

:: Удаляем задачу из планировщика
schtasks /delete /tn AssistantUpdate /f

:: Ждем 2 секунды перед запуском новой версии
timeout /t 2 /nobreak >nul

:: Запускаем новую версию программы
start "" "{os.path.join(self.CURRENT_DIR, "Assistant.exe").replace(os.sep, '/')}"

:: Удаляем архив и временную папку с новой версией
if exist "{new_version_dir.replace(os.sep, '/')}" (
    rmdir /s /q "{new_version_dir.replace(os.sep, '/')}"
)

if exist "{correct_archive_path}" (
    del /q "{correct_archive_path}"
)
"""
        # Сохраняем команду в bat-файл
        with open("update.bat", "w") as f:
            f.write(update_script)

        # Команда для создания задачи в планировщике
        command = [
            "schtasks", "/create", "/tn", "AssistantUpdate", "/tr",
            f'"{os.path.abspath("update.bat")}"', "/sc", "once", "/st",
            time.strftime("%H:%M", time.localtime(time.time() + 60)), "/f", "/RL", "HIGHEST"
        ]

        try:
            # Выполняем команду с флагом CREATE_NO_WINDOW
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            output = result.stdout.decode('cp866')  # Декодируем вывод
            QMessageBox.information(self, "Успех",
                                    "После завершения программы будет установлена новая версия")
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode('cp866')  # Декодируем ошибку
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать задачу: {error_output}")

    def main(self):
        """Основная логика обновления"""
        # Выбираем ZIP-архив с новой версией
        archive_path = self.select_new_version_archive()
        if not archive_path:
            QMessageBox.warning(self, "Ошибка", "Архив с новой версией не выбран.")
            return

        # Создаем временную директорию для распаковки
        temp_extract_dir = os.path.join(os.path.dirname(archive_path), "temp_extract")
        os.makedirs(temp_extract_dir, exist_ok=True)

        # Распаковываем архив
        if not self.extract_archive(archive_path, temp_extract_dir):
            return

        # Создаем задачу в планировщике
        self.create_scheduler_task(archive_path, temp_extract_dir)

        try:
            subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Assistant.exe'], check=True, stdout=subprocess.PIPE)
            audio_paths = self.audio_paths
            restart_file = audio_paths.get('restart_file')
            react_detail(restart_file)
            subprocess.run(['taskkill', '/IM', 'Assistant.exe', '/F'], check=True)
        except subprocess.CalledProcessError:
            QMessageBox.warning(self, "Предупреждение", "Процесс Assistant.exe не найден.")


class LinkProcessWindow(QDialog):
    """ Класс для обработки окна "Процессы ярлыков" """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.base_path = get_base_directory()
        self.process_names_path = self.parent.process_names
        self.process_names = self.load_process_names()
        self.init_ui()

    def load_process_names(self):
        """ Загружает данные о ярлыках и процессах из файла process_names.json """
        if os.path.exists(self.process_names_path):
            with open(self.process_names_path, "r", encoding="utf-8") as file:
                return json.load(file)
        return []

    def save_process_names(self):
        """ Сохраняет данные о ярлыках и процессах в файл process_names.json """
        with open(self.process_names_path, "w", encoding="utf-8") as file:
            json.dump(self.process_names, file, ensure_ascii=False, indent=4)

    def init_ui(self):
        """ Инициализация пользовательского интерфейса """
        self.setWindowTitle("Процессы ярлыков")
        self.setFixedSize(600, 400)

        # Основной вертикальный макет
        main_layout = QVBoxLayout()

        # Лейбл в самом верху окна
        self.description_label = QLabel("Список процессов, которые привязаны к ярлыку (нужны для закрытия)")
        self.description_label.setAlignment(Qt.AlignCenter)  # Выравнивание текста по центру
        self.description_label.setStyleSheet("font-size: 16px;")
        main_layout.addWidget(self.description_label)

        # Горизонтальный макет для левой и правой колонок
        content_layout = QHBoxLayout()

        # Левая колонка: список ярлыков
        left_layout = QVBoxLayout()
        self.processes_label = QLabel("Ярлыки")
        left_layout.addWidget(self.processes_label)
        self.links_list = QListWidget()
        self.links_list.itemClicked.connect(self.on_link_selected)
        left_layout.addWidget(self.links_list)

        # Правая колонка: список процессов
        right_layout = QVBoxLayout()
        self.processes_label = QLabel("Список процессов")
        right_layout.addWidget(self.processes_label)

        self.processes_list = QListWidget()
        right_layout.addWidget(self.processes_list)

        # Кнопки для управления процессами
        self.add_process_button = QPushButton("Добавить процесс")
        self.add_process_button.clicked.connect(self.add_process)
        right_layout.addWidget(self.add_process_button)

        self.remove_process_button = QPushButton("Удалить процесс")
        self.remove_process_button.clicked.connect(self.remove_process)
        right_layout.addWidget(self.remove_process_button)

        # Добавляем левую и правую части в горизонтальный макет
        content_layout.addLayout(left_layout, 1)
        content_layout.addLayout(right_layout, 2)

        # Добавляем горизонтальный макет в основной вертикальный макет
        main_layout.addLayout(content_layout)

        # Устанавливаем основной макет для окна
        self.setLayout(main_layout)

        # Заполняем список ярлыков
        self.update_links_list()

    def update_links_list(self):
        """ Обновляет список ярлыков """
        self.links_list.clear()
        for item in self.process_names:
            for link_name in item.keys():
                self.links_list.addItem(link_name)

    def update_processes_list(self, link_name):
        """ Обновляет список процессов для выбранного ярлыка """
        self.processes_list.clear()
        for item in self.process_names:
            if link_name in item:
                for process in item[link_name]:
                    self.processes_list.addItem(process)
                break

    def on_link_selected(self, item):
        """ Обработка выбора ярлыка """
        link_name = item.text()
        self.update_processes_list(link_name)

    def add_process(self):
        """ Добавляет процесс к выбранному ярлыку """
        current_link = self.links_list.currentItem()
        if not current_link:
            QMessageBox.warning(self, "Ошибка", "Выберите ярлык для добавления процесса.")
            return

        link_name = current_link.text()
        process_name, ok = QInputDialog.getText(self, "Добавить процесс", "Введите название процесса:")
        if ok and process_name:
            for item in self.process_names:
                if link_name in item:
                    if process_name not in item[link_name]:
                        item[link_name].append(process_name)
                        self.update_processes_list(link_name)
                        self.save_process_names()
                    else:
                        QMessageBox.warning(self, "Ошибка", "Процесс с таким именем уже существует.")
                    break

    def remove_process(self):
        """ Удаляет процесс из выбранного ярлыка """
        current_link = self.links_list.currentItem()
        current_process = self.processes_list.currentItem()
        if not current_link or not current_process:
            QMessageBox.warning(self, "Ошибка", "Выберите ярлык и процесс для удаления.")
            return

        link_name = current_link.text()
        process_name = current_process.text()
        for item in self.process_names:
            if link_name in item:
                if process_name in item[link_name]:
                    item[link_name].remove(process_name)
                    self.update_processes_list(link_name)
                    self.save_process_names()
                break

    def closeEvent(self, event):
        """ Сохраняет данные при закрытии окна """
        self.save_process_names()
        super().closeEvent(event)


class OtherOptionsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Прочие опции")
        self.setFixedSize(400, 450)

        # Основной layout
        main_layout = QHBoxLayout(self)

        # Левая колонка с кнопками
        left_column = QVBoxLayout()
        left_column.setAlignment(Qt.AlignTop)  # Выравниваем кнопки по верху
        main_layout.addLayout(left_column, 1)

        # Добавляем линию-разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)  # Вертикальная линия
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Правая колонка с содержимым
        self.right_column = QStackedWidget()
        main_layout.addWidget(self.right_column, 2)

        # Добавляем кнопки и их содержимое
        self.add_tab("Счетчик цензуры", CensorCounterWidget(self))

    def add_tab(self, button_name, content_widget):
        # Создаем кнопку
        button = QPushButton(button_name, self)
        button.clicked.connect(lambda: self.right_column.setCurrentIndex(self.right_column.count() - 1))

        # Добавляем кнопку в левую колонку
        self.layout().itemAt(0).layout().addWidget(button)

        # Добавляем содержимое в правую колонку
        self.right_column.addWidget(content_widget)


class CensorCounterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        # Основной layout
        layout = QVBoxLayout(self)

        # Метки для отображения данных
        self.day_label = QLabel("За день: 0", self)
        self.week_label = QLabel("За последние 7 дней: 0", self)
        self.month_label = QLabel("За последние 30 дней: 0", self)
        self.total_label = QLabel("Всего: 0", self)

        # Добавляем метки в layout
        layout.addWidget(self.day_label)
        layout.addWidget(self.week_label)
        layout.addWidget(self.month_label)
        layout.addWidget(self.total_label)

        self.reset_button = QPushButton("Сбросить счетчик")
        self.reset_button.clicked.connect(self.reset_censor_counter)
        layout.addWidget(self.reset_button)

        layout.addStretch()

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

    def load_data(self):
        # Загружаем данные из CSV-файла
        file_path = os.path.join(self.get_base_directory(), "user_settings", "censor_counter.csv")
        try:
            self.data = pd.read_csv(file_path, parse_dates=["date"])
            self.calculate_scores()
        except Exception as e:
            logger.error(f"Ошибка при загрузке censor_counter.csv: {e}")

    def calculate_scores(self):
        # Текущая дата
        today = datetime.now().date()

        # Данные за день
        day_data = self.data[self.data["date"].dt.date == today]
        day_score = int(day_data["score"].sum())

        # Данные за неделю (последние 7 дней, включая сегодня)
        week_start = today - timedelta(days=6)
        week_data = self.data[self.data["date"].dt.date >= week_start]
        week_score = int(week_data["score"].sum())

        # Данные за месяц (последние 30 дней, включая сегодня)
        month_start = today - timedelta(days=29)
        month_data = self.data[self.data["date"].dt.date >= month_start]
        month_score = int(month_data["score"].sum())

        # Общий счет
        total_score = int(self.data["score"].sum())

        # Обновляем метки
        self.day_label.setText(f"За день: {day_score}")
        self.week_label.setText(f"За последние 7 дней: {week_score}")
        self.month_label.setText(f"За последние 30 дней: {month_score}")
        self.total_label.setText(f"Всего: {total_score}")

    def reset_censor_counter(self):
        """
        Сбрасывает счетчик, обнуляя таблицу censor_counter.csv.
        Оставляет только заголовки.
        """

        # Диалоговое окно с подтверждением
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('Сброс счетчика')
        msg_box.setText("Точно сбросить значения?")
        yes_button = msg_box.addButton("Да", QMessageBox.YesRole)
        no_button = msg_box.addButton("Нет", QMessageBox.NoRole)
        yes_button.setStyleSheet("padding: 1px 10px;")
        no_button.setStyleSheet("padding: 1px 10px;")
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.exec_()

        # Если пользователь нажал "Нет", выходим из метода
        if msg_box.clickedButton() == no_button:
            logger.info("Сброс счетчика отменен.")
            return

        # Путь к CSV-файлу
        CSV_FILE = os.path.join(self.get_base_directory(), 'user_settings', 'censor_counter.csv')

        # Проверяем, существует ли файл
        if not Path(CSV_FILE).exists():
            logger.error("Файл censor_counter.csv не существует. Невозможно сбросить счетчик.")
            return

        # Открываем файл для записи и оставляем только заголовки
        with open(CSV_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['date', 'score', 'total_score'])  # Записываем заголовки

        logger.info("Счетчик успешно сброшен.")

        # Обновляем лейблы после сброса
        self.update_labels()

    def update_labels(self):
        """
        Обновляет лейблы после сброса счетчика.
        """
        try:
            # Обновляем значения в лейблах
            self.day_label.setText("За день: 0")
            self.week_label.setText("За последние 7 дней: 0")
            self.month_label.setText("За последние 30 дней: 0")
            self.total_label.setText("Всего: 0")
        except Exception as e:
            logger.error(f"Ошибка при обновлении лейблов: {e}")


class ChangelogWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("История изменений")
        self.setFixedSize(500, 600)

        # Основной layout
        layout = QVBoxLayout()

        # Текстовое поле для отображения changelog
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        # Кнопка закрытия
        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)

        self.setLayout(layout)

        # Загружаем содержимое файла
        self.load_changelog()

    def load_changelog(self):
        try:
            if os.path.exists(self.parent().changelog_file_path):
                with open(self.parent().changelog_file_path, 'r', encoding='utf-8') as f:
                    self.text_edit.setText(f.read())
            else:
                logger.error("Файл изменений временно недоступен")
        except Exception as e:
            logger.error(f"Ошибка загрузки изменений: {str(e)}")



# Запуск приложения
if __name__ == '__main__':
    app = QApplication([])
    window = Assistant()
    app.exec_()
