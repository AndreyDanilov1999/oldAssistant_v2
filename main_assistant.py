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
from pathlib import Path
import sys
import time
import traceback
import zipfile
import re
import markdown2
import requests
from packaging import version
import psutil
import winsound
from bin.commands_settings_window import CommandSettingsWindow
from bin.other_options_window import OtherOptionsWindow
from bin.func_list import handler_links, handler_folder
from bin.function_list_main import *
from path_builder import get_path
import simpleaudio as sa
import numpy as np
import threading
import pyaudio
import subprocess
from bin.audio_control import controller
from bin.settings_window import MainSettingsWindow
from bin.speak_functions import react, react_detail
from logging_config import logger
from bin.lists import get_audio_paths
from vosk import Model, KaldiRecognizer
from PyQt5.QtGui import QIcon, QCursor, QFont
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, \
                             QPushButton, QCheckBox, QSystemTrayIcon, QAction, qApp, QMenu, QMessageBox, \
                             QTextEdit, QDialog, QLabel, QLineEdit, QFileDialog, QSlider, QStackedWidget, QFrame,
                             QTextBrowser)
from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer, QEvent

speakers = dict(Пласид='placide', Бестия='rogue', Джонни='johnny', СанСаныч='sanych',
                Санбой='sanboy', Тигрица='tigress', Стейтем='stathem')

# Сырая ссылка на version.txt в GitHub
VERSION_FILE_URL = "https://raw.githubusercontent.com/AndreyDanilov1999/oldAssistant_v2/refs/heads/master/version.txt"
CHANGELOG_TXT_URL = "https://raw.githubusercontent.com/AndreyDanilov1999/oldAssistant_v2/refs/heads/master/changelog.txt"
CHANGELOG_MD_URL = "https://raw.githubusercontent.com/AndreyDanilov1999/oldAssistant_v2/refs/heads/master/changelog.md"


class Assistant(QWidget):
    """
Основной класс содержащий GUI и скрипт обработки команд
    """

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
        self.log_file_path = get_path('assistant.log')
        self.init_logger()
        self.settings_file_path = get_path('user_settings', 'settings.json')
        self.update_settings(self.settings_file_path)
        self.settings = self.load_settings()
        self.color_settings_path = get_path('user_settings', 'color_settings.json')
        self.commands = self.load_commands()
        self.default_preset_style = get_path('bin', 'color_presets', 'default.json')
        self.process_names = get_path('user_settings', 'process_names.json')
        self.last_position = 0
        self.steam_path = self.settings.get('steam_path', '')
        self.volume_assist = self.settings.get('volume_assist', 0.2)
        self.is_min_tray = self.settings.get("minimize_to_tray", True)
        self.is_assistant_running = False
        self.show_upd_msg = self.settings.get("show_upd_msg", False)
        self.assistant_thread = None
        self.is_censored = self.settings.get('is_censored', False)
        self.censored_thread = None
        self.speaker = self.settings.get("voice", "johnny")
        self.assistant_name = self.settings.get('assistant_name', "джо")
        self.assist_name2 = self.settings.get('assist_name2', "джо")
        self.assist_name3 = self.settings.get('assist_name3', "джо")
        self.audio_paths = get_audio_paths(self.speaker)
        self.MEMORY_LIMIT_MB = 1024
        self.version = "1.2.8"
        self.ps = "Powered by theoldman"
        self.label_version = QLabel(f"Версия: {self.version} {self.ps}", self)
        self.label_message = QLabel('', self)
        self.initui()
        self.check_or_create_folder()
        self.load_and_apply_styles()
        self.apply_styles()
        # Проверка автозапуска при старте программы
        self.check_autostart()

        # Прятать ли программу в трей
        if self.is_min_tray:
            self.hide()
        else:
            self.showNormal()

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
        self.tray_icon.setIcon(QIcon(get_path('icon_assist.ico')))

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
        self.newsettings_button = QPushButton("Настройки")
        self.newsettings_button.clicked.connect(self.open_main_settings)
        left_layout.addWidget(self.newsettings_button)

        # Кнопка "Ваши команды"
        self.newsettings_button = QPushButton("Ваши команды")
        self.newsettings_button.clicked.connect(self.open_commands_settings)
        left_layout.addWidget(self.newsettings_button)

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
        self.setWindowTitle("Ассистент")
        self.setGeometry(500, 250, 900, 600)

        # Установка иконки для окна
        self.setWindowIcon(QIcon(get_path('icon_assist.ico')))

        # Инициализация FileSystemWatcher
        self.init_file_watcher()

        # Загрузка предыдущих записей из файла логов
        self.load_existing_logs()

        # Таймер для периодической проверки файла
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(1000)  # Проверка каждую секунду

    def show_message(self, text, title="Уведомление", message_type="info", buttons=QMessageBox.Ok):
        """
        Универсальная функция для показа сообщений
        :param text: Текст сообщения
        :param title: Заголовок окна (по умолчанию "Уведомление")
        :param message_type: Тип сообщения ("info", "warning", "error", "question")
        :param buttons: Кнопки (по умолчанию QMessageBox.Ok)
        :return: Результат нажатия кнопки
        """
        # Выбираем звук в зависимости от типа сообщения
        sound = {
            'info': winsound.MB_ICONASTERISK,
            'warning': winsound.MB_ICONEXCLAMATION,
            'error': winsound.MB_ICONHAND,
            'question': winsound.MB_ICONQUESTION
        }.get(message_type, winsound.MB_ICONASTERISK)

        winsound.MessageBeep(sound)

        # Создаем и настраиваем MessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(buttons)

        # Устанавливаем иконку в зависимости от типа
        if message_type == "info":
            msg_box.setIcon(QMessageBox.Information)
        elif message_type == "warning":
            msg_box.setIcon(QMessageBox.Warning)
        elif message_type == "error":
            msg_box.setIcon(QMessageBox.Critical)
        elif message_type == "question":
            msg_box.setIcon(QMessageBox.Question)

        # Стилизация кнопки
        for button in msg_box.buttons():
            button.setStyleSheet("padding: 1px 10px;")

        return msg_box.exec_()

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
        """Проверяет обновления с автоматическим выбором формата changelog"""
        try:
            # Загружаем файл версии
            version_response = requests.get(
                VERSION_FILE_URL,
                timeout=10,
                headers={'Cache-Control': 'no-cache'}
            )
            version_response.raise_for_status()
            version_content = version_response.text.strip()

            # Парсим версию
            version_parts = version_content.split(maxsplit=1)
            if len(version_parts) < 2:
                raise ValueError("Неверный формат файла версии")

            latest_version, latest_version_url = version_parts[0], version_parts[1].strip()
            current_ver = version.parse(self.version)
            latest_ver = version.parse(latest_version)

            # Загружаем changelog
            changelog_response = requests.get(
                CHANGELOG_MD_URL,
                timeout=15,
                headers={'Cache-Control': 'no-cache'}
            )
            changelog_response.raise_for_status()

            # В методе check_for_updates_app:
            changelog_path = os.path.join(tempfile.gettempdir(), 'changelog.md')
            with open(changelog_path, 'w', encoding='utf-8') as f:
                f.write(changelog_response.text)
            logger.info(f"Changelog сохранен в: {changelog_path}")

            self.changelog_file_path = changelog_path
            self.latest_version_url = latest_version_url

            # Сравниваем с последней доступной версией
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
        folder_path = get_path('user_settings', "links for assist")
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

    def close_app(self):
        """Закрытие приложения."""
        self.stop_assist()
        qApp.quit()

    def load_commands(self):
        """Загружает команды из JSON-файла."""
        file_path = get_path('user_settings', 'commands.json')  # Полный путь к файлу
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
            "show_upd_msg": self.show_upd_msg,
            "minimize_to_tray": self.is_min_tray
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
                "show_upd_msg": True,
                "minimize_to_tray": True
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
        CSV_FILE = get_path('user_settings', 'censor_counter.csv')

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
                logger.error(f"Ошибка при обработке строки {row}: {e}")
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
                    logger.error("Превышен лимит памяти")
                    self.stop_assist()
                    self.show_message("Превышен лимит памяти.\nПерезапустите программу", "Ошибка",
                                      "error")
                    break

                if any(keyword in text for keyword in ['сук', 'суч', 'пизд', 'еба', 'ёба',
                                                       'нах', 'ху', 'бля', 'ебу', 'епт',
                                                       'ёпт', 'гандон', 'пид']):
                    self.censor_counter()

                if self.is_censored and any(keyword in text for keyword in ['сук', 'суч', 'пизд', 'еба', 'ёба',
                                                                            'нах', 'ху', 'бля', 'ебу', 'епт',
                                                                            'ёпт', 'гандон', 'пид']):
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
                                folder_processed = self.handle_folder_command(restored_command, action_type)

                                if not folder_processed and not app_processed:
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
                                folder_processed = self.handle_folder_command(command, action_type)

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
            self.show_message(f"Ошибка в основном цикле ассистента: {e}", "Ошибка",
                              "error")

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
            self.show_message(f"Микрофон не обнаружен. Пожалуйста, подключите микрофон и перезагрузите программу.",
                              "Ошибка", "error")
            return False

        model_path_ru = get_path("bin", "model_ru")
        model_path_en = get_path("bin", "model_en")
        logger.info(f"Используются модели:\n RU - {model_path_ru};\n EN - {model_path_en}")

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
                data = self.stream.read(512, exception_on_overflow=False)
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
            self.show_message(f"Ошибка при обработке аудиоданных: {e}", "Ошибка", "error")
        finally:
            logger.info("Остановка аудиопотока...")
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

    def handle_app_command(self, text, action):
        """Обработка команд для приложений"""
        for keyword, filename in self.commands.items():
            if keyword in text:
                if not filename.endswith('.lnk') and not filename.endswith('.url'):
                    return False  # Прекращаем обработку, если это папка
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
        folder_path = get_path('user_settings', "links for assist")
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

    def open_main_settings(self):
        """Обработка нажатия кнопки 'Настройки'"""
        try:
            settings_window = MainSettingsWindow(self)
            # Получаем виджет настроек и подключаем сигнал
            settings_widget = settings_window.get_settings_widget()
            if settings_widget:
                settings_widget.voice_changed.connect(self.update_voice)

            settings_window.exec_()
        except Exception as e:
            logger.error(f"Ошибка при открытии настроек: {e}")
            self.show_message(f"Ошибка при открытии настроек: {e}", "Ошибка", "error")

    def open_commands_settings(self):
        """Обработка нажатия кнопки 'Ваши команды'"""
        try:
            settings_window = CommandSettingsWindow(self)

            settings_window.exec_()
        except Exception as e:
            logger.error(f"Ошибка при открытии настроек команд: {e}")
            self.show_message(f"Ошибка при открытии настроек команд: {e}", "Ошибка", "error")

    def relax_window(self):
        """Обработка нажатия кнопки Релакс"""
        dialog = RelaxWindow(self)
        dialog.exec_()

    def other_options(self):
        """Открываем окно с прочими опциями"""
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
        log_file_path = get_path('assistant.log')  # Используем правильный путь к логам
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
        current_directory = get_path()
        write_directory = os.path.dirname(current_directory)
        # Путь к исполняемому файлу и .bat файлу
        exe_path = os.path.join(write_directory, 'Assistant.exe')
        bat_path = os.path.join(current_directory, 'start_assistant.bat')
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
        logger.info(f"Путь для планировщика: {target_path}")
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
            # self.log_area.append(output)  # Вывод результата
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
            # self.log_area.append(output)  # Вывод результата
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
        self.CURRENT_DIR = os.path.dirname(get_path())

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
                self.show_message(f"В выбранном архиве отсутствует папка _internal.", "Ошибка", "error")
                return False

            # Проверка наличия Assistant.exe
            has_assistant_exe = "Assistant.exe" in file_list
            if not has_assistant_exe:
                self.show_message(f"В выбранном архиве отсутствует файл Assistant.exe.", "Ошибка", "error")
                return False

            return True
        except Exception as e:
            self.show_message(f"Не удалось проверить архив: {str(e)}", "Ошибка", "error")
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
            self.show_message(f"Не удалось распаковать архив: {str(e)}", "Ошибка", "error")
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
            logger.info(output)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Уведомление')
            msg_box.setText(f"После завершения программы будет установлена новая версия")
            ok_button = msg_box.addButton("ОК", QMessageBox.AcceptRole)
            ok_button.setStyleSheet("padding: 1px 10px;")
            QApplication.beep()
            msg_box.exec_()
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode('cp866')  # Декодируем ошибку
            self.show_message(f"Не удалось создать задачу: {error_output}", "Ошибка", "error")

    def main(self):
        """Основная логика обновления"""
        # Выбираем ZIP-архив с новой версией
        archive_path = self.select_new_version_archive()
        if not archive_path:
            self.show_message(f"Архив с новой версией не выбран.", "Предупреждение", "warning")
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
            self.show_message(f"Процесс Assistant.exe не найден.", "Предупреждение", "warning")


class ChangelogWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("История изменений")
        self.setFixedSize(700, 600)  # Увеличенный размер для лучшего отображения

        # Основной layout
        layout = QVBoxLayout()

        # Текстовый браузер с поддержкой HTML
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setReadOnly(True)

        # Стили для Markdown
        self.text_browser.document().setDefaultStyleSheet("""
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                padding: 15px;
            }
            h1 {
                font-size: 24px;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            h2 {
                font-size: 20px;
                margin-top: 25px;
            }
            h3 {
                font-size: 16px;
            }
            code {
                background: #f5f5f5;
                padding: 2px 5px;
                border-radius: 3px;
                font-family: "Courier New", monospace;
            }
            pre {
                background: #f5f5f5;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
            }
            blockquote {
                border-left: 4px solid #ddd;
                padding-left: 15px;
                color: #777;
                margin-left: 0;
            }
            a {
                color: #1e88e5;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            ul, ol {
                padding-left: 25px;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
        """)

        layout.addWidget(self.text_browser)

        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

        self.load_changelog()

    def load_changelog(self):
        """Загружает и отображает Markdown файл"""
        try:
            if not hasattr(self.parent(), 'changelog_file_path'):
                self._show_error("Не указан путь к файлу изменений")
                return

            changelog_path = self.parent().changelog_file_path

            if not os.path.exists(changelog_path):
                self._show_error(f"Файл не найден: {changelog_path}")
                return

            with open(changelog_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # Конвертируем Markdown в HTML
            html = markdown2.markdown(
                md_content,
                extras=[
                    'fenced-code-blocks',  # Блоки кода ```
                    'tables',  # Таблицы
                    'footnotes',  # Сноски
                    'toc',  # Оглавление
                    'cuddled-lists',  # Компактные списки
                    'task_list',  # Списки задач
                    'spoiler'  # Скрытый текст
                ]
            )

            self.text_browser.setHtml(html)

        except Exception as e:
            self._show_error(f"Ошибка загрузки Markdown: {str(e)}")

    def _show_error(self, message):
        """Отображает сообщение об ошибке"""
        self.text_browser.setPlainText(message)


# Запуск приложения
if __name__ == '__main__':
    app = QApplication([])
    window = Assistant()
    app.exec_()
