"""
Этот модуль представляет собой основной файл для работы ассистента.

Здесь реализованы функции и классы, необходимые для
запуска и управления ассистентом, включая обработку
пользовательского ввода и управление интерфейсом.
"""
import csv
import ctypes
import win32clipboard
from PIL import ImageGrab, Image

ctypes.windll.user32.SetProcessDPIAware()
import io
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
import markdown2
import requests
import win32con
import win32gui
from PyQt5.QtSvg import QSvgWidget
from packaging import version
import psutil
import winsound
from bin.commands_settings_window import CommandSettingsWindow
from bin.other_options_window import OtherOptionsWindow
from bin.func_list import handler_links, handler_folder
from bin.function_list_main import *
from path_builder import get_path
import threading
import pyaudio
import subprocess
from bin.audio_control import controller
from bin.settings_window import MainSettingsWindow
from bin.speak_functions import thread_react_detail, thread_react, react
from logging_config import logger, debug_logger
from bin.lists import get_audio_paths
from vosk import Model, KaldiRecognizer
from PyQt5.QtGui import QIcon, QCursor, QFont, QColor, QPixmap
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, \
                             QPushButton, QCheckBox, QSystemTrayIcon, QAction, qApp, QMenu, QMessageBox, \
                             QTextEdit, QDialog, QLabel, QFileDialog, QTextBrowser, QMainWindow, QStyle, QSizePolicy,
                             QGraphicsColorizeEffect)
from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer, QEvent, pyqtSignal

short_name = "https://raw.githubusercontent.com/AndreyDanilov1999/oldAssistant_v2/refs/heads/master/"
# Сырая ссылка на version.txt в GitHub
EXP_VERSION_FILE_URL = f"{short_name}exp-version.txt"
VERSION_FILE_URL = f"{short_name}version.txt"
CHANGELOG_TXT_URL = f"{short_name}changelog.txt"
CHANGELOG_MD_URL = f"{short_name}changelog.md"
MUTEX_NAME = "Assistant_123456789ABC"

def activate_existing_window():
    hwnd = win32gui.FindWindow(None, "Ассистент")
    if not hwnd:
        return False

    # Получаем информацию об окне
    placement = win32gui.GetWindowPlacement(hwnd)

    # Если окно свёрнуто в трей (SW_SHOWMINIMIZED)
    if placement[1] == win32con.SW_SHOWMINIMIZED:
        # Восстанавливаем и активируем
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    else:
        # Если окно просто неактивно - активируем
        win32gui.SetForegroundWindow(hwnd)

    # Дополнительные меры для надёжности
    win32gui.BringWindowToTop(hwnd)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    return True


class Assistant(QMainWindow):
    """
Основной класс содержащий GUI и скрипт обработки команд
    """
    close_child_windows = pyqtSignal()

    def check_memory_usage(self, limit_mb):
        """
        Проверка потребления оперативной памяти
        :param limit_mb:
        :return:
        """
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # В МБ
        if memory_usage > limit_mb:
            debug_logger.error(f"Превышен лимит памяти: {memory_usage} МБ > {limit_mb} МБ")
            return False
        return True

    def __init__(self):
        super().__init__()
        self.version = "1.2.19"
        self.ps = "Powered by theoldman"
        self.label_version = QLabel(f"Версия: {self.version} {self.ps}", self)
        self.label_message = QLabel('', self)
        self.latest_version_url = None
        self.relax_button = None
        self.drag_pos = None  # Для перемещения окна за ЛКМ
        self.open_folder_button = None
        self.beta_version = False
        self.tray_icon = None
        self.toggle_start = None
        self.start_button = None
        self.styles = None
        self._update_dialog = None
        self.changelog_file_path = None
        self.is_assistant_running = False
        self.first_run = True
        self.assistant_thread = None
        self.censored_thread = None
        self.last_position = 0
        self.MEMORY_LIMIT_MB = 1024
        self.log_file_path = get_path('assistant.log')
        self.init_logger()
        self.svg_file_path = get_path("owl.svg")
        self.process_names = get_path('user_settings', 'process_names.json')
        self.color_settings_path = get_path('user_settings', 'color_settings.json')
        self.default_preset_style = get_path('bin', 'color_presets', 'default.json')
        self.settings_file_path = get_path('user_settings', 'settings.json')
        self.screenshot_tool = SystemScreenshot()
        # self.game_mode = None
        # self.game_mode_bool = False
        self.update_settings(self.settings_file_path)
        self.settings = self.load_settings()
        self.assistant_name = self.settings.get('assistant_name', "джо")
        self.assist_name2 = self.settings.get('assist_name2', "джо")
        self.assist_name3 = self.settings.get('assist_name3', "джо")
        self.speaker = self.settings.get("voice", "johnny")
        self.volume_assist = self.settings.get('volume_assist', 0.2)
        self.steam_path = self.settings.get('steam_path', '')
        self.is_censored = self.settings.get('is_censored', False)
        self.show_upd_msg = self.settings.get("show_upd_msg", False)
        self.is_min_tray = self.settings.get("minimize_to_tray", True)
        self.commands = self.load_commands()
        self.audio_paths = get_audio_paths(self.speaker)
        self.initui()
        self.check_or_create_folder()
        self.load_and_apply_styles()
        # Проверка автозапуска при старте программы
        self.check_autostart()
        self.check_start_win()
        # Прятать ли программу в трей
        if self.is_min_tray:
            # Показ окна при первом запуске(для отладки)
            if self.first_run:
                self.preload_window()
            self.hide()
        else:
            self.showNormal()

        self.run_assist()
        self.check_update_label()
        # self.check_for_updates_app()
        QTimer.singleShot(2000, self.check_for_updates_app)

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def initui(self):
        """Инициализация пользовательского интерфейса."""
        self.setWindowIcon(QIcon(get_path('icon_assist.ico')))
        self.setWindowTitle("Ассистент")
        # Убираем стандартную рамку окна
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Главный контейнер с фоном
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        # Настройки окна
        self.resize(900, 650)
        # Центрирование окна
        screen_geometry = self.screen().availableGeometry()
        self.move(
            (screen_geometry.width() - self.width()) // 2,
            (screen_geometry.height() - self.height()) // 2
        )

        # Главный вертикальный макет
        root_layout = QVBoxLayout(self.central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Title Bar ---
        self.title_bar_widget = QWidget()
        self.title_bar_widget.setObjectName("TitleBar")
        self.title_bar_layout = QHBoxLayout(self.title_bar_widget)
        self.title_bar_layout.setContentsMargins(10, 5, 10, 5)

        # Добавляем иконку в заголовок
        icon_label = QLabel()
        icon_pixmap = QPixmap(get_path('icon_assist.ico')).scaled(20, 20,
                                                                  Qt.AspectRatioMode.KeepAspectRatio,
                                                                  Qt.TransformationMode.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        self.title_bar_layout.addWidget(icon_label)

        self.title_label = QLabel("Ассистент")
        self.title_label.setContentsMargins(0, 0, 0, 0)
        self.title_bar_layout.addWidget(self.title_label)

        self.title_bar_layout.addStretch()

        self.start_win_btn = QPushButton()
        self.start_win_btn.setFixedSize(25, 25)
        self.start_win_btn.setStyleSheet("background: transparent;")
        self.start_win_btn.clicked.connect(self.toggle_start_win)
        # Добавляем SVG на кнопку
        self.start_svg = QSvgWidget("start-win.svg", self.start_win_btn)
        self.start_svg.setFixedSize(13, 13)
        self.start_svg.move(6, 6)  # Центрирование
        self.title_bar_layout.addWidget(self.start_win_btn)

        # Кнопка "Свернуть"
        self.minimize_button = QPushButton("─")
        self.minimize_button.setObjectName("TrayButton")
        self.minimize_button.clicked.connect(self.custom_hide)
        self.minimize_button.setFixedSize(25, 25)
        self.title_bar_layout.addWidget(self.minimize_button)

        # Кнопка "Закрыть"
        self.close_button = QPushButton("✕")
        self.close_button.clicked.connect(self.close)
        self.close_button.setFixedSize(25, 25)
        self.close_button.setObjectName("CloseButton")
        self.title_bar_layout.addWidget(self.close_button)

        root_layout.addWidget(self.title_bar_widget)

        # --- Основное содержимое ---
        self.content_widget = QWidget()
        self.content_widget.setObjectName("ContentWidget")
        main_layout = QHBoxLayout(self.content_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # Левая панель (кнопки)
        self.start_button = QPushButton("Старт ассистента")
        self.start_button.clicked.connect(self.start_assist_toggle)
        left_layout.addWidget(self.start_button)

        self.open_folder_button = QPushButton("Ваши ярлыки")
        self.open_folder_button.clicked.connect(self.open_folder_shortcuts)
        left_layout.addWidget(self.open_folder_button)

        self.open_folder_button = QPushButton("Скриншоты")
        self.open_folder_button.clicked.connect(self.open_folder_screenshots)
        left_layout.addWidget(self.open_folder_button)

        self.settings_button = QPushButton("Настройки")
        self.settings_button.clicked.connect(self.open_main_settings)
        left_layout.addWidget(self.settings_button)

        self.commands_button = QPushButton("Ваши команды")
        self.commands_button.clicked.connect(self.open_commands_settings)
        left_layout.addWidget(self.commands_button)

        self.other_button = QPushButton("Прочее")
        self.other_button.clicked.connect(self.other_options)
        left_layout.addWidget(self.other_button)

        left_layout.addStretch()

        self.svg_image = QSvgWidget()
        self.svg_image.load(self.svg_file_path)
        self.svg_image.setStyleSheet("""
            background: transparent;
            border: none;
            outline: none;
        """)
        self.color_svg = QGraphicsColorizeEffect()
        self.svg_image.setGraphicsEffect(self.color_svg)
        left_layout.addWidget(self.svg_image)

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

        # Правая панель (логи)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas"))
        self.log_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.clear_logs_button = QPushButton("Очистить логи")
        self.clear_logs_button.clicked.connect(self.clear_logs)

        right_layout.addWidget(self.log_area)
        right_layout.addWidget(self.clear_logs_button)

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 3)
        root_layout.addWidget(self.content_widget)

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

        # Инициализация FileSystemWatcher
        self.init_file_watcher()

        # Загрузка предыдущих записей из файла логов
        self.load_existing_logs()

        # Таймер для проверки файла логов
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_for_updates)
        self.timer.start(2000)

    def preload_window(self):
        """Предварительная загрузка окна"""
        # Показываем в невидимой области
        self.move(-10000, -10000)
        self.showMinimized()
        self.showNormal()

        # Принудительная отрисовка
        self.update()
        QApplication.processEvents()

        # Скрываем через короткое время
        QTimer.singleShot(100, lambda: [self.hide(), self.center_window()])
        self.first_run = False

    def center_window(self):
        """Центрирование окна"""
        frame_geo = self.frameGeometry()
        screen = QApplication.primaryScreen().availableGeometry()
        frame_geo.moveCenter(screen.center())
        self.move(frame_geo.topLeft())

    def show_message(self, text, title="Уведомление", message_type="info", buttons=QMessageBox.Ok):
        """
        Кастомное окно сообщений
        """
        # Звуковое сопровождение (оставляем как было)
        sound = {
            'info': winsound.MB_ICONASTERISK,
            'warning': winsound.MB_ICONEXCLAMATION,
            'error': winsound.MB_ICONHAND,
            'question': winsound.MB_ICONQUESTION
        }.get(message_type, winsound.MB_ICONASTERISK)
        winsound.MessageBeep(sound)

        # Создаем кастомное окно вместо QMessageBox
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground)
        dialog.setFixedSize(300, 200)

        # Основной контейнер с рамкой 1px
        container = QWidget(dialog)
        container.setObjectName("MessageContainer")
        container.setGeometry(0, 0, dialog.width(), dialog.height())

        title_bar = QWidget(container)
        title_bar.setObjectName("TitleBar")
        title_bar.setGeometry(1, 1, dialog.width() - 2, 35)

        # Горизонтальный layout как у вас было
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setObjectName("TitleLable")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(25, 25)
        close_btn.clicked.connect(dialog.reject)
        title_layout.addWidget(close_btn)

        # ЦЕНТРАЛЬНЫЙ СЛОЙ: Контент (иконка + текст)
        content_widget = QWidget(container)
        content_widget.setObjectName("ContentMessage")
        content_widget.setGeometry(
            1,  # X: 1px от левого края
            36,  # Y: 1px бордер + 35px заголовка
            dialog.width() - 2,  # Ширина минус бордер
            dialog.height() - 36 - 45  # Высота: общая - заголовок - место для кнопок
        )

        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 5, 10, 5)
        content_layout.setSpacing(10)

        # Иконка
        icon_widget = QWidget()
        icon_widget.setFixedSize(50, 50)

        icon = self.style().standardIcon({
                                             "info": QStyle.SP_MessageBoxInformation,
                                             "warning": QStyle.SP_MessageBoxWarning,
                                             "error": QStyle.SP_MessageBoxCritical,
                                             "question": QStyle.SP_MessageBoxQuestion
                                         }.get(message_type, QStyle.SP_MessageBoxInformation))

        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(40, 40))
        # icon_label.setAlignment(Qt.AlignCenter)

        icon_layout = QVBoxLayout(icon_widget)
        icon_layout.addWidget(icon_label)
        content_layout.addWidget(icon_widget)

        # Текст
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # text_label.setAlignment(Qt.AlignVCenter)
        content_layout.addWidget(text_label)

        # НИЖНИЙ СЛОЙ: Кнопки
        button_widget = QWidget(container)
        button_widget.setGeometry(
            1,  # X: 1px от левого края
            dialog.height() - 45,  # Y: отступаем 45px снизу (35px кнопки + 10px отступ)
            dialog.width() - 2,  # Ширина минус бордер
            35  # Высота блока кнопок
        )

        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        # Добавляем stretch для центрирования кнопок
        button_layout.addStretch()

        if buttons == QMessageBox.Ok:
            btn = QPushButton("OK")
            btn.clicked.connect(dialog.accept)
            button_layout.addWidget(btn)
        elif buttons == QMessageBox.Yes | QMessageBox.No:
            btn_yes = QPushButton("Да")
            btn_yes.clicked.connect(dialog.accept)
            button_layout.addWidget(btn_yes)

            btn_no = QPushButton("Нет")
            btn_no.clicked.connect(dialog.reject)
            button_layout.addWidget(btn_no)

        button_layout.addStretch()

        for btn in button_widget.findChildren(QPushButton):
            btn.setStyleSheet("""
                    QPushButton {
                        padding: 1px 10px;
                        min-width: 60px
                    }
                """)

        # Позиционируем окно по центру родителя
        if self.parent():
            parent_rect = self.parent().geometry()
            dialog.move(
                parent_rect.center() - dialog.rect().center()
            )

        return dialog.exec_()

    def keyPressEvent(self, event):
        """Сворачивает основное окно в трей по нажатию на Esc"""
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Если есть дочерние окна — отправляем сигнал на закрытие
            if any(child.isVisible() for child in self.findChildren(QDialog)):
                self.close_child_windows.emit()  # Закрываем все дочерние окна
                event.accept()
                return

            # Иначе перемещаем окно
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def open_download_link(self, event):
        """Открывает ссылку на скачивание при клике на текст."""
        if self.update_label.text() == "Установлена последняя версия":
            audio_paths = self.audio_paths
            update_button = audio_paths.get('update_button')
            thread_react_detail(update_button)
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
            self.check_update_label()
            # Выбираем URL в зависимости от режима проверки
            version_url = EXP_VERSION_FILE_URL if self.beta_version else VERSION_FILE_URL
            # Загружаем файл версии
            version_response = requests.get(
                version_url,
                timeout=10,
                headers={'Cache-Control': 'no-cache'}
            )
            version_response.raise_for_status()
            version_content = version_response.text.strip()

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

            changelog_path = os.path.join(tempfile.gettempdir(), 'changelog.md')
            with open(changelog_path, 'w', encoding='utf-8') as f:
                f.write(changelog_response.text)
            debug_logger.debug(f"Changelog сохранен в: {changelog_path}")

            self.changelog_file_path = changelog_path
            self.latest_version_url = latest_version_url

            # Сравниваем с последней доступной версией
            if latest_ver > current_ver:
                self.update_label.setText("Доступна новая версия")
                self.check_update_label()
                if self.settings.get("show_upd_msg", True):
                    self.show_update_notification(latest_version)
            else:
                self.update_label.setText("Установлена последняя версия")

        except requests.Timeout:
            logger.warning("Таймаут при проверке обновлений")
            debug_logger.warning("Таймаут при проверке обновлений")
            self.update_label.setText("Ошибка соединения")
        except requests.RequestException as e:
            logger.error(f"Ошибка сети: {str(e)}")
            debug_logger.warning(f"Ошибка сети: {str(e)}")
            self.update_label.setText("Нет соединения")
        except ValueError as e:
            logger.error(f"Ошибка формата данных: {str(e)}")
            debug_logger.warning(f"Ошибка формата данных: {str(e)}")
            self.update_label.setText("Ошибка данных")
        except Exception as e:
            logger.error(f"Неожиданная ошибка")
            debug_logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
            self.update_label.setText("Ошибка обновления")

    def handle_message_click(self, latest_version):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(100, lambda: self.show_popup(latest_version))

    def show_update_notification(self, latest_version):
        """Показ уведомления о новой версии"""
        if not self.isVisible():  # Если окно скрыто в трее
            # Показываем message в трее
            self.tray_icon.showMessage(
                "Доступно обновление",
                "Нажмите для подробностей",
                QSystemTrayIcon.Information,
                3000  # 3 секунды
            )
            self.tray_icon.messageClicked.connect(
                lambda: self.handle_message_click(latest_version)
            )
        else:
            # Если окно видимо - показываем обычный диалог
            self.show_popup(latest_version)

    def show_popup(self, latest_version):
        """Кастомное окно обновления"""
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setFixedSize(450, 200)
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        dialog.move(
            screen_geometry.center() - dialog.rect().center()
        )

        # Основной контейнер с рамкой
        container = QWidget(dialog)
        container.setObjectName("MessageContainer")
        container.setGeometry(0, 0, dialog.width(), dialog.height())

        # Заголовок с крестиком
        title_bar = QWidget(container)
        title_bar.setObjectName("TitleBar")
        title_bar.setGeometry(1, 1, dialog.width() - 2, 35)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)

        title_label = QLabel("Доступно обновление")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(25, 25)
        close_btn.setObjectName("CloseButton")
        close_btn.clicked.connect(dialog.reject)
        title_layout.addWidget(close_btn)

        # Основное содержимое
        content_widget = QWidget(container)
        content_widget.setGeometry(1, 36, dialog.width() - 2, dialog.height() - 37)

        # Вертикальный layout
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Текст сообщения
        text_label = QLabel(
            f"<b>Доступна новая версия: {latest_version}</b>"
            "<p>Хотите скачать обновление?</p>"
        )
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

        # Чекбокс
        checkbox = QCheckBox("Больше не показывать")
        layout.addWidget(checkbox, 0, Qt.AlignLeft)

        btn_frame = QWidget()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        changes_btn = QPushButton("Список изменений")
        install_btn = QPushButton("Установить")
        later_btn = QPushButton("Позже")

        # Делаем кнопки одинаковой ширины
        for btn in [changes_btn, install_btn, later_btn]:
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(30)

        btn_layout.addWidget(changes_btn)
        btn_layout.addWidget(install_btn)
        btn_layout.addWidget(later_btn)
        layout.addWidget(btn_frame)

        # Обработчики
        def on_changes():
            self.changelog_window(None)

        def on_install():
            webbrowser.open(self.latest_version_url)
            if checkbox.isChecked():
                self.show_upd_msg = False
                self.save_settings()
            dialog.accept()

        def on_later():
            if checkbox.isChecked():
                self.show_upd_msg = False
                self.save_settings()
            dialog.reject()

        changes_btn.clicked.connect(on_changes)
        install_btn.clicked.connect(on_install)
        later_btn.clicked.connect(on_later)

        # Позиционирование
        if self.parent():
            dialog.move(
                self.parent().geometry().center() - dialog.rect().center()
            )
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        dialog.exec_()

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

        # Проверяем, существует ли папка
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            debug_logger.info("Папка links for assist найдена")
        else:
            # Если папка не существует, создаем её
            try:
                os.makedirs(folder_path)  # Создаем папку
                debug_logger.info('Папка "links for assist" была создана.')
                debug_logger.info(f"Путь хранения ярлыков: {folder_path}")
            except Exception as e:
                logger.error(f'Ошибка при создании папки для хранения ярлыков: {e}')
                debug_logger.error(f'Ошибка при создании папки для хранения ярлыков: {e}')

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
        self.apply_color_svg(self.color_settings_path, self.svg_image)

    def apply_styles(self):
        # Устанавливаем objectName для виджетов
        if hasattr(self, 'central_widget'):
            self.central_widget.setObjectName("CentralWidget")
        if hasattr(self, 'title_bar_widget'):
            self.title_bar_widget.setObjectName("TitleBar")
        if hasattr(self, 'container'):
            self.title_bar_widget.setObjectName("ConfirmDialogContainer")
        # Применяем стили к текущему окну
        style_sheet = ""
        for widget, styles in self.styles.items():
            if widget.startswith("Q"):  # Для стандартных виджетов (например, QMainWindow, QPushButton)
                selector = widget
            else:  # Для виджетов с objectName (например, TitleBar, CentralWidget)
                selector = f"#{widget}"

            style_sheet += f"{selector} {{\n"
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

    def apply_color_svg(self, style_file: str, svg_widget: QSvgWidget, strength: float = 0.93) -> None:
        """Читает цвет из JSON-файла стилей"""
        with open(style_file) as f:
            styles = json.load(f)

        if "TitleBar" in styles and "border-bottom" in styles["TitleBar"]:
            border_parts = styles["TitleBar"]["border-bottom"].split()
            for part in border_parts:
                if part.startswith('#'):
                    color_effect = QGraphicsColorizeEffect()
                    color_effect.setColor(QColor(part))
                    svg_widget.setGraphicsEffect(color_effect)
                    color_effect.setStrength(strength)
                    break

    def close_app(self):
        """Закрытие приложения."""
        self.stop_assist()
        qApp.quit()

    def load_commands(self):
        """Загружает команды из JSON-файла."""
        file_path = get_path('user_settings', 'commands.json')  # Полный путь к файлу
        try:
            if not os.path.exists(file_path):
                logger.info(f"Файл {file_path} не найден.")
                debug_logger.debug(f"Файл {file_path} не найден.")
                return {}  # Возвращаем пустой словарь, если файл не найден

            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()  # Читаем содержимое и убираем пробелы
                if not content:  # Если файл пустой
                    return {}  # Возвращаем пустой словарь
                return json.loads(content)  # Загружаем JSON
        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл {file_path} содержит некорректный JSON.")
            debug_logger.error(f"Ошибка: файл {file_path} содержит некорректный JSON.")
            return {}  # Возвращаем пустой словарь при ошибке декодирования
        except Exception as e:
            logger.error(f"Ошибка при загрузке команд из файла {file_path}: {e}")
            debug_logger.error(f"Ошибка при загрузке команд из файла {file_path}: {e}")
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
            "minimize_to_tray": self.is_min_tray,
            "start_win": self.toggle_start
        }
        try:
            # Проверяем, существует ли папка user_settings
            os.makedirs(os.path.dirname(self.settings_file_path), exist_ok=True)

            # Сохраняем настройки в файл
            with open(self.settings_file_path, 'w', encoding='utf-8') as file:
                json.dump(settings_data, file, ensure_ascii=False, indent=4)

            logger.info("Настройки сохранены.")
            debug_logger.debug("Настройки сохранены.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {e}")
            debug_logger.error(f"Ошибка при сохранении настроек: {e}")
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
        if reason == QSystemTrayIcon.Trigger:  # Одинарный щелчок
            if self.isVisible():
                # Если окно видимо - сворачиваем
                self.hide()
            else:
                # Если окно скрыто - разворачиваем
                self.showNormal()
                self.show()
                self.activateWindow()

    def custom_hide(self):
        self.close_child_windows.emit()
        self.hide()

    def changeEvent(self, event):
        """Обработка изменения состояния окна."""
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                self.hide()
        super().changeEvent(event)

    def closeEvent(self, event):
        """Обработка закрытия окна с кастомным диалогом подтверждения"""
        self.close_child_windows.emit()
        if self.is_assistant_running:
            dialog = QDialog(self)
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            dialog.setAttribute(Qt.WA_TranslucentBackground)
            dialog.setFixedSize(250, 150)

            # Основной контейнер с рамкой 1px
            container = QWidget(dialog)
            container.setObjectName("MessageContainer")
            container.setGeometry(0, 0, dialog.width(), dialog.height())

            # Заголовок
            title_bar = QWidget(container)
            title_bar.setObjectName("TitleBar")
            title_bar.setGeometry(1, 1, dialog.width() - 2, 35)
            title_layout = QHBoxLayout(title_bar)
            title_layout.setContentsMargins(10, 5, 10, 5)
            title_layout.setSpacing(5)

            title_label = QLabel("Подтверждение")
            title_layout.addWidget(title_label)
            title_layout.addStretch()

            close_btn = QPushButton("✕")
            close_btn.setFixedSize(25, 25)
            close_btn.setObjectName("CloseButton")
            close_btn.clicked.connect(lambda: self.handle_close_confirmation(False, event, dialog))
            title_layout.addWidget(close_btn)

            # Основное содержимое
            content_widget = QWidget(container)
            content_widget.setGeometry(1, 36, dialog.width() - 2, dialog.height() - 37)

            # Вертикальный layout для содержимого
            layout = QVBoxLayout(content_widget)
            layout.setContentsMargins(10, 5, 10, 5)
            layout.setSpacing(10)

            # Текст сообщения
            message_label = QLabel("Вы уверены, что хотите закрыть?")
            message_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(message_label)

            # Горизонтальный layout для кнопок
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)

            # Кнопки
            yes_button = QPushButton("Да")
            yes_button.setFixedSize(80, 25)
            yes_button.setObjectName("ConfirmButton")
            yes_button.clicked.connect(lambda: self.handle_close_confirmation(True, event, dialog))

            no_button = QPushButton("Нет")
            no_button.setFixedSize(80, 25)
            no_button.setObjectName("RejectButton")
            no_button.clicked.connect(lambda: self.handle_close_confirmation(False, event, dialog))

            button_layout.addWidget(yes_button)
            button_layout.addWidget(no_button)
            button_layout.setAlignment(Qt.AlignCenter)

            layout.addLayout(button_layout)

            # Позиционируем диалог
            if self.parent():
                parent_rect = self.parent().geometry()
                dialog.move(
                    parent_rect.center() - dialog.rect().center()
                )

            dialog.exec_()
        else:
            event.accept()

    def handle_close_confirmation(self, confirmed, event, dialog):
        """Обрабатывает ответ пользователя"""
        dialog.close()
        if confirmed:
            self.stop_assist()  # Ваш метод для остановки ассистента
            event.accept()
        else:
            event.ignore()

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
        react(close_assist_folder)

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
                debug_logger.error(f"Ошибка в методе censor_counter при обработке строки {row}: {e}")
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
                    debug_logger.info("Сброс контекста из-за неактивности (7 секунд)")
                    continue

                if not self.is_assistant_running:
                    break

                # Обновляем время последней активности при получении текста
                last_activity_time = current_time

                # Проверка памяти и цензуры (без изменений)
                if not self.check_memory_usage(self.MEMORY_LIMIT_MB):
                    logger.error("Превышен лимит памяти")
                    debug_logger.error("Превышен лимит памяти")
                    self.stop_assist()
                    self.show_message("Превышен лимит памяти.\nПерезапустите программу", "Ошибка",
                                      "error")
                    break

                if any(keyword in text for keyword in ['сук', 'суч', 'пизд', 'еба', 'ёба',
                                                       'нах', 'хуй', 'бля', 'ебу', 'епт',
                                                       'ёпт', 'гандон', 'пид']):
                    self.censor_counter()

                if self.is_censored and any(keyword in text for keyword in ['сук', 'суч', 'пизд', 'еба', 'ёба',
                                                                            'нах', 'хуй', 'бля', 'ебу', 'епт',
                                                                            'ёпт', 'гандон', 'пид']):
                    censored_folder = self.audio_paths.get('censored_folder')
                    thread_react(censored_folder)
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
                                'пейнт': (open_paint, close_paint),
                                'переменные': (open_path, None),
                                'диспетчер': (open_taskmgr, close_taskmgr),
                                'корзин': (open_recycle_bin, close_recycle_bin),
                                'дат': (open_appdata, close_appdata),
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
                                debug_logger.info(f"Восстановленная команда: {restored_command}")

                                # Определяем тип действия
                                action_type = last_unrecognized_command['action_type']

                                # Пытаемся обработать как приложение
                                app_processed = self.handle_app_command(restored_command, action_type)
                                folder_processed = self.handle_folder_command(restored_command, action_type)

                                if not folder_processed and not app_processed:
                                    logger.warning(f"Не удалось обработать команду: {restored_command}")
                                    debug_logger.warning(f"Не удалось обработать команду: {restored_command}")
                                    what_folder = self.audio_paths.get('what_folder')
                                    if what_folder:
                                        thread_react(what_folder)
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
                            elif 'корзин' in command:
                                if action_type == 'open':
                                    open_recycle_bin()
                                else:
                                    close_recycle_bin()
                            elif 'дат' in command:
                                if action_type == 'open':
                                    open_appdata()
                                else:
                                    close_appdata()
                            # elif 'игровой режим' in command:
                            #     if action_type == 'open':
                            #         self.start_game_mode()
                            #     else:
                            #         self.stop_game_mode()
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
                                    thread_react(approve_folder)
                                search_yandex(query)
                            elif "фулл скрин" in command:
                                self.capture_fullscreen()
                            elif "скрин" in command:
                                self.capture_area()
                            else:
                                echo_folder = self.audio_paths.get('echo_folder')
                                if echo_folder:
                                    thread_react(echo_folder)

                    if reaction_triggered:
                        what_folder = self.audio_paths.get('what_folder')
                        if what_folder:
                            thread_react(what_folder)
                        if self.speaker == "sanboy" and random.random() <= 0.7:
                            prorok_sanboy = self.audio_paths.get('prorok_sanboy')
                            thread_react_detail(prorok_sanboy)

                # Обработка плеера (без изменений)
                if 'плеер' in text:
                    if any(keyword in text for keyword in
                           ['пауз', 'пуск', 'пуст', 'вкл', 'вруб', 'отруб', 'выкл', 'стоп']):
                        controller.play_pause()
                        player_folder = self.audio_paths.get('player_folder')
                        thread_react(player_folder)
                    elif any(keyword in text for keyword in ['след', 'впер', 'дальш', 'перекл']):
                        controller.next_track()
                        player_folder = self.audio_paths.get('player_folder')
                        thread_react(player_folder)
                    elif any(keyword in text for keyword in ['пред', 'назад']):
                        controller.previous_track()
                        player_folder = self.audio_paths.get('player_folder')
                        thread_react(player_folder)


                # elif self.game_mode_bool:
                #     found_cmd = self.game_mode.find_command(text)
                #     if not found_cmd:
                #         logger.info("Команда не распознана")
                #         continue
                #     if "сброс" in text:
                #         self.game_mode.cleanup()
                #         logger.info("Все кнопки отпущены")
                #     elif "держи" in text:
                #         self.game_mode.trigger(found_cmd, hold=True)
                #         logger.info(f"Удерживаю {found_cmd}")
                #     else:
                #         self.game_mode.trigger(found_cmd)
                #         logger.info(f"Нажимаю {found_cmd}")


        except Exception as e:
            logger.error(f"Ошибка в основном цикле ассистента: {e}")
            debug_logger.error(f"Ошибка в основном цикле ассистента: {e}")
            debug_logger.error(traceback.format_exc())
            self.show_message(f"Ошибка в основном цикле ассистента: {e}", "Ошибка",
                              "error")

    # "Основной цикл ассистента(конец)"
    # "--------------------------------------------------------------------------------------------------"
    # "Основной цикл ассистента(конец)"

    # def install_game_mode(self):
    #     try:
    #         self.game_mode = GamepadManager()
    #         if self.game_mode.init_success:
    #             logger.info("Игровой режим успешно инициализирован")
    #         else:
    #             logger.warning("Не удалось инициализировать игровой режим")
    #             self.game_mode = None
    #     except Exception as e:
    #         logger.error(f"Ошибка при инициализации GamepadManager: {e}")
    #         self.game_mode = None
    #
    # def start_game_mode(self):
    #     self.install_game_mode()
    #     self.game_mode.set_game("God of War")
    #     logger.info(self.game_mode)
    #     logger.info(self.game_mode.running)
    #     if self.game_mode and not self.game_mode.running:
    #         self.game_mode.start_proxy()
    #         self.game_mode_bool = True
    #         logger.info("Игровой режим активирован")
    #     else:
    #         logger.warning("Невозможно активировать игровой режим")
    #
    # def stop_game_mode(self):
    #     if self.game_mode and self.game_mode.running:
    #         self.game_mode.stop_proxy()
    #         self.game_mode.cleanup()
    #         self.game_mode_bool = False
    #         logger.info("Игровой режим деактивирован")

    def check_microphone_available(self):
        """Проверка наличия микрофона в системе."""
        p = pyaudio.PyAudio()
        try:
            # Получаем информацию об устройстве ввода по умолчанию
            default_input_device = p.get_default_input_device_info()
            logger.info(f"Устройство ввода: {default_input_device.get('name')}")
            debug_logger.info(f"Устройство ввода: {default_input_device.get('name')}")
            return True
        except IOError:
            # Если устройство по умолчанию не найдено
            logger.warning("Микрофон не обнаружен.")
            debug_logger.warning("Микрофон не обнаружен.")
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
        logger.info("Загрузка моделей для распознавания...")
        debug_logger.debug("Загрузка моделей для распознавания...")
        model_path_ru = get_path("bin", "model_ru")
        model_path_en = get_path("bin", "model_en")
        debug_logger.debug(f"Загружена модель RU - {model_path_ru}")
        debug_logger.debug(f"Загружена модель EN - {model_path_en}")

        try:
            # Преобразуем путь в UTF-8
            model_path_ru_utf8 = model_path_ru.encode("utf-8").decode("utf-8")
            model_path_en_utf8 = model_path_en.encode("utf-8").decode("utf-8")

            # Пытаемся загрузить модель
            self.model_ru = Model(model_path_ru_utf8)
            self.model_en = Model(model_path_en_utf8)
            logger.info("Модели успешно загружены.")
            debug_logger.info("Модели успешно загружены.")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}. Возможно путь содержит кириллицу.")
            debug_logger.error(f"Ошибка при загрузке модели: {e}. Возможно путь содержит кириллицу.")
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
                    debug_logger.info(f"Распознано (RU): {ru_text}")
                elif en_text:  # Если русского нет, используем английский
                    final_text = en_text
                    logger.info(f"Распознано (EN): {en_text}")
                    debug_logger.info(f"Распознано (EN): {en_text}")

                if final_text:
                    yield final_text

        except Exception as e:
            error_file = self.audio_paths.get('error_file')
            thread_react_detail(error_file)
            logger.error(f"Ошибка при обработке аудиоданных: {e}")
            debug_logger.error(f"Ошибка при обработке аудиоданных: {e}")
            debug_logger.error(traceback.format_exc())
            self.show_message(f"Ошибка при обработке аудиоданных: {e}", "Ошибка", "error")
        finally:
            logger.info("Остановка аудиопотока...")
            debug_logger.info("Остановка аудиопотока...")
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

    def open_folder_shortcuts(self):
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
                logger.info(f'Папка "{folder_path}" была создана.')
                debug_logger.info(f'Папка "{folder_path}" была создана.')
                os.startfile(folder_path)  # Открываем папку после создания
            except Exception as e:
                logger.error(f'Ошибка при создании папки: {e}')
                debug_logger.error(f'Ошибка при создании папки: {e}')

    def open_folder_screenshots(self):
        """Обработка нажатия кнопки 'Открыть папку с ярлыками'"""
        folder_path = get_path('user_settings', "screenshots")
        self.log_area.append(folder_path)

        # Проверяем, существует ли папка
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            os.startfile(folder_path)  # Открываем папку
        else:
            # Если папка не существует, создаем её
            try:
                os.makedirs(folder_path)  # Создаем папку
                logger.info(f'Папка "{folder_path}" была создана.')
                debug_logger.info(f'Папка "{folder_path}" была создана.')
                os.startfile(folder_path)  # Открываем папку после создания
            except Exception as e:
                logger.error(f'Ошибка при создании папки: {e}')
                debug_logger.error(f'Ошибка при создании папки: {e}')

    def open_main_settings(self):
        """Обработка нажатия кнопки 'Настройки'"""
        try:
            settings_window = MainSettingsWindow(self)
            # Получаем виджет настроек и подключаем сигнал
            settings_widget = settings_window.get_settings_widget()
            if settings_widget:
                settings_widget.voice_changed.connect(self.update_voice)

            settings_window.show()
        except Exception as e:
            debug_logger.error(f"Ошибка при открытии настроек: {e}")
            self.show_message(f"Ошибка при открытии настроек: {e}", "Ошибка", "error")

    def open_commands_settings(self):
        """Обработка нажатия кнопки 'Ваши команды'"""
        try:
            settings_window = CommandSettingsWindow(self)

            settings_window.exec_()
        except Exception as e:
            debug_logger.error(f"Ошибка при открытии настроек команд: {e}")
            self.show_message(f"Ошибка при открытии настроек команд: {e}", "Ошибка", "error")

    def other_options(self):
        """Открываем окно с прочими опциями"""
        try:
            other_window = OtherOptionsWindow(self)
            other_window.show()
        except Exception as e:
            debug_logger.error(f"Ошибка при открытии прочих опций: {e}")
            self.show_message(f"Ошибка при открытии прочих опций: {e}", "Ошибка", "error")

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
        debug_logger.info(f"Голос изменен на: {new_voice}")

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

    def check_start_win(self):
        """Переключает состояние и меняет цвет иконки"""
        if self.toggle_start:
            self.update_svg_color(self.start_svg, self.color_settings_path)
        else:
            self.update_svg_contrast_color(self.start_svg)

    def toggle_start_win(self):
        """Переключает состояние и меняет цвет иконки"""
        self.toggle_start = not self.toggle_start

        if self.toggle_start:
            self.add_to_autostart()
            self.update_svg_color(self.start_svg, self.color_settings_path)
        else:
            self.remove_from_autostart()
            self.update_svg_contrast_color(self.start_svg)

    def update_svg_color(self, svg_widget: QSvgWidget, style_file: str) -> None:
        """Обновляет цвет SVG на цвет из настроек (специально для вашего SVG)"""
        try:
            # 1. Получаем цвет из JSON
            with open(style_file) as f:
                styles = json.load(f)

            # Ищем цвет в border-bottom свойствах TitleBar
            border_bottom = styles.get("TitleBar", {}).get("border-bottom", "")
            new_color = next((p for p in border_bottom.split() if p.startswith("#")), "#FFFFFF")

            # Ищем цвет в border-bottom свойствах TitleBar
            bg_color = styles.get("QWidget", {}).get("background-color", "")
            base_bg_color = next((p for p in bg_color.split() if p.startswith("#")), "#FFFFFF")
            base_bg_color = QColor(base_bg_color)

            # 2. Вычисляем яркость фона (формула восприятия яркости)
            brightness = (0.299 * base_bg_color.red() +
                          0.587 * base_bg_color.green() +
                          0.114 * base_bg_color.blue()) / 255

            # 3. Выбираем контрастный цвет
            final_color = "#369EFF" if brightness > 0.5 else new_color

            # 2. Загружаем стандартный SVG (ваш XML)
            svg_template = '''<?xml version="1.0" encoding="utf-8"?>
            <svg fill="{color}" width="20px" height="20px" viewBox="0 0 24 24" 
                 xmlns="http://www.w3.org/2000/svg">
                <path d="m9.84 12.663v9.39l-9.84-1.356v-8.034zm0-10.72v9.505h-9.84v-8.145zm14.16 10.72v11.337l-13.082-1.803v-9.534zm0-12.663v11.452h-13.082v-9.649z"/>
            </svg>'''

            # 3. Вставляем нужный цвет
            colored_svg = svg_template.format(color=final_color)

            # 4. Обновляем виджет
            svg_widget.load(colored_svg.encode('utf-8'))

        except Exception as e:
            logger.error(f"Ошибка при обновлении цвета SVG: {e}")
            debug_logger.error(f"Ошибка при обновлении цвета SVG: {e}")

    def update_svg_contrast_color(self, svg_widget: QSvgWidget) -> None:
        """Автоматически устанавливает контрастный цвет для SVG"""
        # 1. Определяем цвет фона основного окна
        bg_color = self.central_widget.palette().window().color()

        # 2. Вычисляем яркость фона (формула восприятия яркости)
        brightness = (0.299 * bg_color.red() +
                      0.587 * bg_color.green() +
                      0.114 * bg_color.blue()) / 255

        # 3. Выбираем контрастный цвет
        contrast_color = "#545454" if brightness > 0.5 else "#FFFFFF"

        # 4. Обновляем SVG
        try:
            svg_template = '''<?xml version="1.0" encoding="utf-8"?>
                        <svg fill="{color}" width="20px" height="20px" viewBox="0 0 24 24" 
                             xmlns="http://www.w3.org/2000/svg">
                            <path d="m9.84 12.663v9.39l-9.84-1.356v-8.034zm0-10.72v9.505h-9.84v-8.145zm14.16 10.72v11.337l-13.082-1.803v-9.534zm0-12.663v11.452h-13.082v-9.649z"/>
                        </svg>'''
            colored_svg = svg_template.format(color=contrast_color)
            svg_widget.load(bytes(colored_svg, 'utf-8'))
        except Exception:
            # Fallback - используем эффект цвета
            effect = QGraphicsColorizeEffect()
            effect.setColor(QColor(contrast_color))
            svg_widget.setGraphicsEffect(effect)

    def add_to_autostart(self):
        """Добавление программы в автозапуск через планировщик задач"""
        current_directory = get_path()
        write_directory = os.path.dirname(current_directory)

        # Базовые имена задач
        task_name_base = "VirtualAssistant"

        # Определяем тип запуска и пути
        if getattr(sys, 'frozen', False):
            # Запуск как EXE
            task_name = task_name_base
            target_path = os.path.join(write_directory, 'Assistant.exe')
        else:
            # Запуск как скрипт Python
            task_name = f"{task_name_base}-script"
            bat_path = os.path.join(current_directory, 'start_assistant.bat')

            # Создаем BAT-файл если его нет
            if not os.path.isfile(bat_path):
                try:
                    with open(bat_path, 'w', encoding='utf-8') as bat_file:
                        bat_file.write(f'@echo off\npython "{os.path.abspath(__file__)}"')
                    debug_logger.info(f"Создан .bat файл: {bat_path}")
                except Exception as e:
                    debug_logger.error(f"Ошибка при создании .bat файла: {e}")
                    return

            target_path = bat_path

        logger.info(f"Путь для планировщика: {target_path}")
        debug_logger.debug(f"Путь для планировщика: {target_path}")

        # Проверка наличия файла
        if not os.path.isfile(target_path):
            error_msg = f"Ошибка: Файл '{target_path}' не найден."
            logger.error(error_msg)
            debug_logger.error(error_msg)
            return

        # Команда для создания задачи в планировщике
        command = [
            'schtasks',
            '/create',
            '/tn', task_name,
            '/tr', f'"{target_path}"',  # Путь в кавычках для поддержки пробелов
            '/sc', 'onlogon',
            '/rl', 'highest',
            '/f'
        ]

        try:
            result = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                encoding='cp866'
            )

            success_msg = f"Программа добавлена в автозапуск"
            logger.info(success_msg)
            debug_logger.info(success_msg)

        except subprocess.CalledProcessError as e:
            error_msg = f"Ошибка при добавлении в автозапуск: {e.stderr}"
            logger.error(error_msg)
            debug_logger.error(error_msg)

    def remove_from_autostart(self):
        """Удаление программы из автозапуска через планировщик задач"""
        # Определяем имя задачи в зависимости от типа запуска
        if getattr(sys, 'frozen', False):
            task_name = "VirtualAssistant"  # Для EXE-версии
        else:
            task_name = "VirtualAssistant-script"  # Для Python-скрипта

        command = [
            'schtasks',
            '/delete',
            '/tn', task_name,
            '/f'
        ]

        try:
            result = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                encoding='cp866'
            )
            success_msg = f"Задача '{task_name}' удалена из автозапуска"
            debug_logger.info(success_msg)
            self.log_area.append(success_msg)
        except subprocess.CalledProcessError as e:
            if "не существует" not in e.stderr:
                error_msg = f"Ошибка при удалении задачи '{task_name}': {e.stderr}"
                debug_logger.error(error_msg)
                self.log_area.append(error_msg)
            else:
                debug_logger.info(f"Задача '{task_name}' не найдена в планировщике")

    def check_autostart(self):
        """Проверка, добавлена ли программа в автозапуск"""
        # Определяем имя задачи в зависимости от типа запуска
        if getattr(sys, 'frozen', False):
            task_name = "VirtualAssistant"  # Для EXE-версии
        else:
            task_name = "VirtualAssistant-script"  # Для Python-скрипта

        command = ['schtasks', '/query', '/tn', task_name]

        try:
            result = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                encoding='cp866'
            )
            debug_logger.info(f"Найдена задача автозапуска: '{task_name}'")
            self.toggle_start = True
            self.save_settings()
        except subprocess.CalledProcessError as e:
            if "не существует" not in e.stderr:
                error_msg = f"Ошибка при проверке задачи '{task_name}': {e.stderr}"
                logger.error(error_msg)
                debug_logger.error(error_msg)
            self.toggle_start = False
            self.save_settings()
            debug_logger.info(f"Задача '{task_name}' не найдена в планировщике")

    def capture_area(self):
        try:
            approve_folder = self.audio_paths.get('approve_folder')
            thread_react(approve_folder)
            self.screenshot_tool.capture_area()
        except Exception as e:
            logger.error(f'Ошибка {e}')
            debug_logger.error(f'Ошибка {e}')

    def capture_fullscreen(self):
        try:
            self.screenshot_tool.capture_fullscreen()
            approve_folder = self.audio_paths.get('approve_folder')
            thread_react(approve_folder)
        except Exception as e:
            logger.error(f'Ошибка {e}')
            debug_logger.error(f'Ошибка {e}')


class UpdateApp(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
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
        russian_letters = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        if any(char in russian_letters for char in archive_path):
            self.assistant.show_message("Путь к архиву содержит русские символы...", "Ошибка", "error")
            return False

        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()

            # Проверка наличия папки _internal
            has_internal = any(file.startswith("_internal/") for file in file_list)
            if not has_internal:
                self.assistant.show_message(f"В выбранном архиве отсутствует папка _internal.", "Ошибка", "error")
                return False

            # Проверка наличия Assistant.exe
            has_assistant_exe = "Assistant.exe" in file_list
            if not has_assistant_exe:
                self.assistant.show_message(f"В выбранном архиве отсутствует файл Assistant.exe.", "Ошибка", "error")
                return False

            return True
        except Exception as e:
            self.assistant.show_message(f"Не удалось проверить архив: {str(e)}", "Ошибка", "error")
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
            debug_logger.error(f"Не удалось распаковать архив: {str(e)}")
            self.assistant.show_message(f"Не удалось распаковать архив: {str(e)}", "Ошибка", "error")
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
            debug_logger.info(f"Вывод в методе create_scheduler_task: {output}")
            self.assistant.show_message(f"После завершения программы будет установлена новая версия")
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode('cp866')  # Декодируем ошибку
            self.assistant.show_message(f"Не удалось создать задачу: {error_output}", "Ошибка", "error")

    def main(self):
        """Основная логика обновления"""
        # Выбираем ZIP-архив с новой версией
        archive_path = self.select_new_version_archive()
        if not archive_path:
            self.assistant.show_message(f"Архив с новой версией не выбран.", "Предупреждение", "warning")
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
            thread_react_detail(restart_file)
            subprocess.run(['taskkill', '/IM', 'Assistant.exe', '/F'], check=True)
        except subprocess.CalledProcessError:
            self.assistant.show_message(f"Процесс Assistant.exe не найден.", "Предупреждение", "warning")


class ChangelogWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(700, 600)

        # Основной контейнер с рамкой
        container = QWidget(self)
        container.setObjectName("MessageContainer")
        container.setGeometry(0, 0, self.width(), self.height())

        # Заголовок с крестиком
        title_bar = QWidget(container)
        title_bar.setObjectName("TitleBar")
        title_bar.setGeometry(1, 1, self.width() - 2, 35)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(5)

        title_label = QLabel("История изменений")
        title_label.setObjectName("TitleLabel")
        title_label.setFixedSize(150, 20)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(25, 25)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)

        # Основное содержимое
        content_widget = QWidget(container)
        content_widget.setGeometry(1, 36, self.width() - 2, self.height() - 37)

        # Вертикальный layout
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Текстовый браузер
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setReadOnly(True)
        layout.addWidget(self.text_browser)

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

        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

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


class SystemScreenshot:
    def __init__(self, save_dir=get_path("user_settings", "screenshots")):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def capture_area(self):
        """Захват области с надежной проверкой буфера"""
        try:
            # Очищаем буфер перед захватом
            self._clear_clipboard()

            # Вызываем системный инструмент
            self._press_win_shift_s()
            logger.info("Выделите область на экране...")
            debug_logger.info("Выделите область на экране...")

            # Ждем и сохраняем с улучшенной проверкой
            return self._wait_and_save_screenshot()
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            debug_logger.error(f"Ошибка: {e}")
            return None

    def capture_fullscreen(self):
        """Захват всего экрана через Win+PrtScn"""
        try:
            # Очищаем буфер перед захватом
            self._clear_clipboard()
            self._press_win_prtscn()
            time.sleep(1)
            return self._wait_and_save_screenshot()
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            debug_logger.error(f"Ошибка: {e}")
            return None

    def _press_win_shift_s(self):
        """Нажатие Win+Shift+S"""
        ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # Win
        ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # Shift
        ctypes.windll.user32.keybd_event(0x53, 0, 0, 0)  # S
        time.sleep(0.1)
        ctypes.windll.user32.keybd_event(0x53, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)

    def _press_win_prtscn(self):
        """Нажатие Win+PrtScn"""
        ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # Win
        ctypes.windll.user32.keybd_event(0x2C, 0, 0, 0)  # PrtScn
        time.sleep(0.1)
        ctypes.windll.user32.keybd_event(0x2C, 0, 2, 0)
        ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)

    def _move_latest_screenshot(self):
        """Переносит последний скриншот из стандартной папки"""
        try:
            pics_dir = os.path.join(os.environ['USERPROFILE'], 'Pictures', 'Screenshots')
            if os.path.exists(pics_dir):
                files = [f for f in os.listdir(pics_dir) if f.lower().endswith('.png')]
                if files:
                    latest = max(
                        [os.path.join(pics_dir, f) for f in files],
                        key=os.path.getctime
                    )
                    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    new_path = os.path.join(self.save_dir, filename)
                    os.rename(latest, new_path)
                    return new_path
        except Exception as e:
            logger.error(f"Ошибка переноса: {e}")
            debug_logger.error(f"Ошибка переноса: {e}")
        return None

    def _get_clipboard_sequence(self):
        """Получаем номер последовательности буфера обмена"""
        try:
            win32clipboard.OpenClipboard()
            return win32clipboard.GetClipboardSequenceNumber()
        finally:
            win32clipboard.CloseClipboard()

    def _clear_clipboard(self):
        """Очищаем буфер обмена"""
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
        finally:
            win32clipboard.CloseClipboard()

    def _get_image_from_clipboard(self):
        """Улучшенное получение изображения из буфера обмена"""
        try:
            win32clipboard.OpenClipboard()

            # Проверяем доступные форматы
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                # Работаем с DIB (Device Independent Bitmap)
                try:
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                    if isinstance(data, bytes):
                        # Создаем BMP-файл в памяти
                        bmp_header = b'BM' + (len(data) + 14).to_bytes(4,
                                                                       'little') + b'\x00\x00\x00\x00\x36\x00\x00\x00'
                        bmp_data = bmp_header + data
                        return Image.open(io.BytesIO(bmp_data))
                except Exception as e:
                    logger.error(f"Ошибка обработки DIB: {e}")
                    debug_logger.error(f"Ошибка обработки DIB: {e}")

            # Альтернативный способ через ImageGrab
            try:
                image = ImageGrab.grabclipboard()
                if image:
                    return image
            except Exception as e:
                logger.error(f"Ошибка ImageGrab: {e}")
                debug_logger.error(f"Ошибка ImageGrab: {e}")

            # Проверяем PNG (если доступен)
            png_format = win32clipboard.RegisterClipboardFormat("PNG")
            if win32clipboard.IsClipboardFormatAvailable(png_format):
                try:
                    data = win32clipboard.GetClipboardData(png_format)
                    if isinstance(data, bytes):
                        return Image.open(io.BytesIO(data))
                except Exception as e:
                    logger.error(f"Ошибка обработки PNG: {e}")
                    debug_logger.error(f"Ошибка обработки PNG: {e}")

        except Exception as e:
            logger.error(f"Ошибка доступа к буферу: {e}")
            debug_logger.error(f"Ошибка доступа к буферу: {e}")
        finally:
            win32clipboard.CloseClipboard()

        return None

    def _wait_and_save_screenshot(self, timeout=5):
        """Улучшенная версия с проверкой последовательности буфера"""
        start_time = time.time()
        last_sequence = -1

        while time.time() - start_time < timeout:
            try:
                # Проверяем номер последовательности буфера
                current_sequence = self._get_clipboard_sequence()

                # Если буфер изменился
                if current_sequence != last_sequence:
                    image = self._get_image_from_clipboard()
                    if image:
                        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        filepath = os.path.join(self.save_dir, filename)
                        image.save(filepath, "PNG")
                        return filepath

                    last_sequence = current_sequence

            except Exception as e:
                debug_logger.error(f"Ошибка проверки буфера: {e}")

            time.sleep(0.3)

        logger.error("Таймаут: скриншот не обнаружен")
        debug_logger.error("Таймаут: скриншот не обнаружен")
        return None


if __name__ == '__main__':
    try:
        if activate_existing_window():
            sys.exit(0)
        app = QApplication([])
        app.setWindowIcon(QIcon(get_path('icon_assist.ico')))
        window = Assistant()

        app.exec_()

    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")
        debug_logger.error(f"Произошла ошибка: {e}")
