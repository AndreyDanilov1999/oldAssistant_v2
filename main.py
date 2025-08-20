"""
Этот модуль представляет собой основной файл для работы ассистента.

Здесь реализованы функции и классы, необходимые для
запуска и управления ассистентом, включая обработку
пользовательского ввода и управление интерфейсом.
"""
import csv
import ctypes
import re
import shutil
import numpy as np
import win32clipboard
from PIL import ImageGrab, Image
from bin.apply_color_methods import ApplyColor
from bin.check_update import load_changelog, VersionCheckThread
from bin.download_thread import DownloadThread, SliderProgressBar
from bin.init import InitScreen
from bin.signals import gui_signals, color_signal, progress_signal, commands_signal
from bin.toast_notification import ToastNotification, SimpleNotice
from bin.widget_window import SmartWidget
ctypes.windll.user32.SetProcessDPIAware()
import io
import json
import logging
import os.path
import random
from pathlib import Path
import sys
import time
import traceback
import zipfile
import markdown2
import win32con
import win32gui
from PyQt5.QtSvg import QSvgWidget
from packaging import version
import psutil
from bin.commands_widgets import CreateCommandsWidget, CommandsWidget, ProcessLinksWidget
from bin.other_options_widgets import CensorCounterWidget, CheckUpdateWidget, DebugLoggerWidget, \
    RelaxWidget
from bin.func_list import handler_links, handler_folder, get_config_value, set_config_value, update_version
from bin.function_list_main import *
from path_builder import get_path
import threading
import sounddevice as sd
import subprocess
from bin.audio_control import controller
from bin.settings_widgets import SettingsWidget, InterfaceWidget, OtherSettingsWidget
from bin.speak_functions import thread_react_detail, thread_react, react
from logging_config import logger, debug_logger
from bin.lists import get_audio_paths
from vosk import Model, KaldiRecognizer
from PyQt5.QtGui import QIcon, QCursor, QFont, QColor, QDesktopServices
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, \
                             QPushButton, QCheckBox, QSystemTrayIcon, QAction, qApp, QMenu, QMessageBox, \
                             QTextEdit, QDialog, QLabel, QTextBrowser, QMainWindow, QSizePolicy,
                             QGraphicsColorizeEffect, QTabWidget, QSpacerItem, QTabBar)
from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer, QEvent, pyqtSignal, QPropertyAnimation, \
    QEasingCurve, pyqtSlot, QUrl

MUTEX_NAME = "Assistant_123456789AB"
build_ini = get_config_value("app", "build")
version_file = "1.5.1"
update_version(version_file)

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
    save_settings_signal = pyqtSignal()
    update_checked = pyqtSignal(bool, str)

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
        self.version = self.get_version()
        self.ps = "Powered by theoldman"
        self.label_version = QLabel(f"Версия: {self.version} {self.ps}", self)
        self.label_message = QLabel('', self)
        self.latest_version_url = None
        self.relax_button = None
        self.drag_pos = None
        self.beta_version = False
        self.tray_icon = None
        self.toggle_start = None
        self.start_button = None
        self._update_dialog = None
        self.changelog_file_path = None
        self.is_assistant_running = False
        self.microphone_available = True
        self.first_run = True
        self.assistant_thread = None
        self.censored_thread = None
        self._current_panel = None
        self.widget_window = None
        self.is_manual_check = False
        gui_signals.open_widget_signal.connect(self.open_widget)
        gui_signals.close_widget_signal.connect(self.close_widget)
        color_signal.color_changed.connect(self.update_colors)
        commands_signal.commands_updated.connect(self.save_commands)
        self.update_checked.connect(self.handle_update_status)
        self.close_child_windows.connect(self.hide_widget)
        self.last_position = 0
        self.MEMORY_LIMIT_MB = 1024
        self.log_file_path = get_path('assistant.log')
        self.init_logger()
        self.svg_file_path = get_path("owl.svg")
        self.install_icons()
        self.process_names = get_path('user_settings', 'process_names.json')
        self.ohm_path = get_path("bin", "OHM", "OpenHardwareMonitor.exe")
        self.style_manager = ApplyColor(self)
        self.color_path = self.style_manager.color_path
        self.styles = self.style_manager.load_styles()
        self.settings_file_path = get_path('user_settings', 'settings.json')
        self.screenshot_tool = SystemScreenshot()
        # self.game_mode = None
        # self.game_mode_bool = False
        self.update_settings(self.settings_file_path)
        self.assistant_name = None
        self.assist_name2 = None
        self.assist_name3 = None
        self.speaker = None
        self.volume_assist = None
        self.steam_path = None
        self.is_censored = None
        self.run_updater = None
        self.is_min_tray = None
        self.is_widget = None
        self.input_device_id = None
        self.input_device_name = None
        self.install_settings()
        self.audio_stream = None
        self.last_audio_time = None  # Время последнего НЕтихого пакета
        self.silence_timer = QTimer()  # Таймер для проверки тишины
        self.silence_timer.timeout.connect(self.check_silence_timeout)
        self.silence_timer.start(5000)
        self.save_settings_signal.connect(self.restart_bot)
        self.type_version = "stable"
        self.commands = self.load_commands()
        self.audio_paths = get_audio_paths(self.speaker)
        self.initui()
        self.splash = InitScreen()
        self.splash.init_complete.connect(self.handle_init_result)
        self.splash.show()
        self.splash.start_checks(self)

    def check_up(self):
        self.check_or_create_folder()
        self.apply_styles()
        # Проверка автозапуска при старте программы
        self.check_autostart()
        self.check_start_win()
        self.check_start_widget()
        # Прятать ли программу в трей
        if self.is_min_tray:
            # Показ окна при первом запуске(для отладки)
            if self.first_run:
                self.preload_window()
        else:
            self.showNormal()
        self.run_assist()
        self.toggle_update_button()
        QTimer.singleShot(2000, lambda: self.check_update_app())
        self.update_checker = QTimer()
        self.update_checker.timeout.connect(self.check_update_app)
        self.update_checker.start(1800000)  # Чек обновлений раз в 30 минут (1800000)

    def handle_init_result(self, success):
        """Обработчик результата инициализации"""
        if success:
            self.check_up()

    def get_version(self):
        vers_on_ini = get_config_value("app", "version")

        if not vers_on_ini or vers_on_ini != version_file:
            set_config_value("app", "version", f"{version_file}")
            return version_file
        return version_file

    def title_bar_mouse_press(self, event):
        """Обработка нажатия мыши на заголовок"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouse_move(self, event):
        """Обработка перемещения мыши при удерживании на заголовке"""
        if self.drag_pos and event.buttons() == Qt.LeftButton:
            # Получаем новую позицию основного окна
            new_pos = event.globalPos() - self.drag_pos
            self.move(new_pos)

            event.accept()

    def title_bar_mouse_release(self, event):
        """Обработка отпускания кнопки мыши"""
        self.drag_pos = None
        event.accept()

    def install_settings(self):
        self.settings = self.load_settings()
        self.assistant_name = self.settings.get('assistant_name', "джо")
        self.assist_name2 = self.settings.get('assist_name2', "джо")
        self.assist_name3 = self.settings.get('assist_name3', "джо")
        self.speaker = self.settings.get("voice", "johnny")
        self.volume_assist = self.settings.get('volume_assist', 0.2)
        self.steam_path = self.settings.get('steam_path', '')
        self.is_censored = self.settings.get('is_censored', False)
        self.run_updater = self.settings.get("run_updater", True)
        self.is_min_tray = self.settings.get("minimize_to_tray", False)
        self.is_widget = self.settings.get("is_widget", True)
        self.input_device_id = self.settings.get("input_device_id", None)
        self.input_device_name = self.settings.get("input_device_name", None)

    def install_icons(self):
        self.icon_start_win = get_path("bin", "icons", "start-win.svg")
        self.icon_update = get_path("bin", "icons", "install-btn.svg")
        self.icon_settings_path = get_path("bin", "icons", "settings.svg")
        self.icon_shortcut_path = get_path("bin", "icons", "shortcut.svg")
        self.icon_power_path = get_path("bin", "icons", "power.svg")
        self.icon_guide_path = get_path("bin", "icons", "guide.svg")
        self.icon_other_path = get_path("bin", "icons", "other.svg")
        self.icon_commands_path = get_path("bin", "icons", "commands.svg")
        self.icon_widget_path = get_path("bin", "icons", "open_widget.svg")
        self.icon_close_path = get_path("bin", "icons", "close.svg")
        self.icon_screenshot_path = get_path("bin", "icons", "camera.svg")
        self.icon_tray_path = get_path("bin", "icons", "tray_icon.png")
        self.icon_updates_path = get_path("bin", "icons", "updates.svg")
        self.icon_advance_settings_path = get_path("bin", "icons", "settings+.svg")
        self.icon_styles_path = get_path("bin", "icons", "styles.svg")
        self.icon_logs_path = get_path("bin", "icons", "logs.svg")
        self.icon_censor_path = get_path("bin", "icons", "censor.svg")
        self.icon_relax_path = get_path("bin", "icons", "relax.svg")
        self.icon_create_command_path = get_path("bin", "icons", "commands.svg")
        self.icon_added_commands_path = get_path("bin", "icons", "commands_list.svg")
        self.icon_process_link_path = get_path("bin", "icons", "process_link.svg")

    def initui(self):
        """Инициализация пользовательского интерфейса."""
        try:
            # Убираем стандартную рамку окна
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.setWindowIcon(QIcon(get_path('icon_assist.ico')))
            self.setWindowTitle("Ассистент")
            self.resize(900, 650)

            # Центрирование окна
            screen_geometry = self.screen().availableGeometry()
            self.move(
                (screen_geometry.width() - self.width()) // 2,
                (screen_geometry.height() - self.height()) // 2
            )
            self.setMouseTracking(True)
            self.drag_pos = None

            # Главный контейнер
            self.central_widget = QWidget()
            self.central_widget.setObjectName("CentralWidget")
            self.setCentralWidget(self.central_widget)

            # Главный layout
            root_layout = QVBoxLayout(self.central_widget)
            root_layout.setContentsMargins(0, 0, 0, 0)
            root_layout.setSpacing(0)

            # --- Title Bar ---
            self.title_bar_widget = QWidget()
            self.title_bar_widget.setObjectName("TitleBar")
            self.title_bar_layout = QHBoxLayout(self.title_bar_widget)
            self.title_bar_layout.setContentsMargins(10, 5, 10, 5)

            self.title_bar_widget.mousePressEvent = self.title_bar_mouse_press
            self.title_bar_widget.mouseMoveEvent = self.title_bar_mouse_move
            self.title_bar_widget.mouseReleaseEvent = self.title_bar_mouse_release

            self.icon_svg = QSvgWidget(self.svg_file_path)
            self.icon_svg.setFixedSize(20, 20)
            self.icon_svg.setStyleSheet("background: transparent;")
            self.title_bar_layout.addWidget(self.icon_svg)

            self.title_label = QLabel("Ассистент")
            self.title_label.setStyleSheet("background: transparent;")
            self.title_bar_layout.addWidget(self.title_label)
            self.title_bar_layout.addStretch()

            self.update_btn = QPushButton()
            self.update_btn.setCursor(QCursor(Qt.PointingHandCursor))
            self.update_btn.setFixedSize(25, 25)
            self.update_btn.clicked.connect(self.open_update_app)
            self.update_btn.hide()
            self.update_svg = QSvgWidget(self.icon_update, self.update_btn)
            self.update_svg.setFixedSize(17, 17)
            self.update_svg.move(4, 4)
            self.update_svg.setStyleSheet("background: transparent;")
            self.title_bar_layout.addWidget(self.update_btn)

            self.start_win_btn = QPushButton()
            self.start_win_btn.setCursor(QCursor(Qt.PointingHandCursor))
            self.start_win_btn.setFixedSize(25, 25)
            self.start_win_btn.clicked.connect(self.toggle_start_win)
            self.start_svg = QSvgWidget(self.icon_start_win, self.start_win_btn)
            self.start_svg.setFixedSize(13, 13)
            self.start_svg.move(6, 6)
            self.start_svg.setStyleSheet("background: transparent;")
            self.title_bar_layout.addWidget(self.start_win_btn)

            self.close_button = QPushButton("✕")
            self.close_button.setCursor(QCursor(Qt.PointingHandCursor))
            self.close_button.clicked.connect(self.custom_hide)
            self.close_button.setFixedSize(25, 25)
            self.close_button.setObjectName("CloseButton")
            self.title_bar_layout.addWidget(self.close_button)

            root_layout.addWidget(self.title_bar_widget)

            # --- Основное содержимое ---
            self.content_widget = QWidget()
            self.content_widget.setObjectName("ContentWidget")
            main_layout = QHBoxLayout(self.content_widget)
            main_layout.setContentsMargins(5, 5, 5, 5)

            # === ЛЕВАЯ ЧАСТЬ: Контейнер с динамической шириной ===
            self.left_container = QWidget()
            self.left_container.setMaximumWidth(250)
            self.left_container_layout = QVBoxLayout(self.left_container)
            self.left_container_layout.setContentsMargins(5, 5, 5, 5)
            self.left_container_layout.setSpacing(10)

            # === 1. Основные кнопки ===
            self.left_buttons_panel = QWidget()
            self.buttons_layout = QVBoxLayout(self.left_buttons_panel)
            self.buttons_layout.setContentsMargins(0, 0, 0, 0)
            self.buttons_layout.setSpacing(10)

            self.settings_button = QPushButton("Настройки")
            self.settings_button.clicked.connect(self.open_main_settings)
            self.settings_button.setStyleSheet("height: 40px; width:240px;")
            self.settings_svg = QSvgWidget(self.icon_settings_path, self.settings_button)
            self.settings_svg.setFixedSize(30, 30)
            self.settings_svg.move(10, 5)
            self.settings_svg.setStyleSheet("background:transparent;")
            self.buttons_layout.addWidget(self.settings_button)

            self.shortcuts_button = QPushButton("Ваши ярлыки")
            self.shortcuts_button.clicked.connect(self.open_folder_shortcuts)
            self.shortcuts_button.setStyleSheet("height: 40px;")
            self.shortcut_svg = QSvgWidget(self.icon_shortcut_path, self.shortcuts_button)
            self.shortcut_svg.setFixedSize(30, 30)
            self.shortcut_svg.move(10, 5)
            self.shortcut_svg.setStyleSheet("background:transparent;")
            self.buttons_layout.addWidget(self.shortcuts_button)

            self.commands_button = QPushButton("Ваши команды")
            self.commands_button.clicked.connect(self.open_commands_settings)
            self.commands_button.setStyleSheet("height: 40px;")
            self.commands_svg = QSvgWidget(self.icon_commands_path, self.commands_button)
            self.commands_svg.setFixedSize(30, 30)
            self.commands_svg.move(10, 5)
            self.commands_svg.setStyleSheet("background:transparent;")
            self.buttons_layout.addWidget(self.commands_button)

            self.other_button = QPushButton("Прочее")
            self.other_button.clicked.connect(self.other_options)
            self.other_button.setStyleSheet("height: 40px;")
            self.other_svg = QSvgWidget(self.icon_other_path, self.other_button)
            self.other_svg.setFixedSize(30, 30)
            self.other_svg.move(10, 5)
            self.other_svg.setStyleSheet("background:transparent;")
            self.buttons_layout.addWidget(self.other_button)

            self.guide_button = QPushButton("Обучение")
            self.guide_button.clicked.connect(self.guide_options)
            self.guide_button.setStyleSheet("height: 40px;")
            self.guide_svg = QSvgWidget(self.icon_guide_path, self.guide_button)
            self.guide_svg.setFixedSize(30, 30)
            self.guide_svg.move(10, 5)
            self.guide_svg.setStyleSheet("background:transparent;")
            self.buttons_layout.addWidget(self.guide_button)

            self.start_button = QPushButton("Старт ассистента")
            self.start_button.clicked.connect(self.start_assist_toggle)
            self.start_button.setStyleSheet("height: 40px;")
            self.power_svg = QSvgWidget(self.icon_power_path, self.start_button)
            self.power_svg.setFixedSize(30, 30)
            self.power_svg.move(10, 5)
            self.power_svg.setStyleSheet("background:transparent;")
            self.buttons_layout.addWidget(self.start_button)

            self.open_widget_btn = QPushButton("Открыть виджет")
            self.open_widget_btn.clicked.connect(self.open_widget)
            self.open_widget_btn.setStyleSheet("height: 40px;")
            self.widget_svg = QSvgWidget(self.icon_widget_path, self.open_widget_btn)
            self.widget_svg.setFixedSize(30, 30)
            self.widget_svg.move(10, 5)
            self.widget_svg.setStyleSheet("background:transparent;")
            self.buttons_layout.addWidget(self.open_widget_btn)

            self.buttons_layout.addStretch()

            self.svg_image = QSvgWidget()
            self.svg_image.load(self.svg_file_path)
            self.svg_image.setFixedSize(180, 180)
            self.svg_image.setStyleSheet("background: transparent; border: none;")
            self.color_svg = QGraphicsColorizeEffect()
            self.svg_image.setGraphicsEffect(self.color_svg)
            self.buttons_layout.addWidget(self.svg_image, alignment=Qt.AlignCenter)

            self.progress_load = SliderProgressBar(self)
            self.progress_load.hide()
            self.buttons_layout.addWidget(self.progress_load)

            self.update_label = QLabel("Установлена последняя версия")
            self.update_label.setCursor(QCursor(Qt.PointingHandCursor))
            self.update_label.mousePressEvent = self.update_answer
            self.buttons_layout.addWidget(self.update_label)

            self.label_version.setCursor(QCursor(Qt.PointingHandCursor))
            self.label_version.mousePressEvent = self.changelog_window
            self.buttons_layout.addWidget(self.label_version)

            # Добавляем панель кнопок в контейнер
            self.left_container_layout.addWidget(self.left_buttons_panel)

            # === 2. Панель настроек (изначально скрыта) ===
            self.mutable_panel = QWidget()
            self.mutable_layout = QVBoxLayout(self.mutable_panel)
            self.mutable_layout.setContentsMargins(5, 5, 5, 5)
            self.mutable_panel.hide()

            self.left_container_layout.addWidget(self.mutable_panel)

            # === ПРАВАЯ ЧАСТЬ: Логи + иконки ===
            self.right_layout = QVBoxLayout()
            self.right_layout.setContentsMargins(5, 5, 5, 5)

            # Компактная панель (иконки)
            self._setup_compact_toolbar()
            self.right_layout.addLayout(self.compact_layout)
            self.hide_layout(self.compact_layout)

            # Логи
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            self.log_area.setFont(QFont("Consolas"))
            self.log_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.clear_logs_button = QPushButton("Очистить логи")
            self.clear_logs_button.clicked.connect(self.clear_logs)
            self.right_layout.addWidget(self.log_area)
            self.right_layout.addWidget(self.clear_logs_button)

            # === Добавляем в main_layout ===
            main_layout.addWidget(self.left_container)
            main_layout.addLayout(self.right_layout)

            root_layout.addWidget(self.content_widget)

            # === Анимация ширины ===
            self.animation = QPropertyAnimation(self.left_container, b"maximumWidth")
            self.animation.setDuration(300)
            self.animation.setEasingCurve(QEasingCurve.OutBack)

            # === Tray, логи, прочее ===
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon(self.icon_tray_path))
            self.tray_icon.setToolTip("Ассистент")

            check_micro = QAction("Найти микрофон", self)
            check_micro.triggered.connect(self._check_microphone_wrapper)

            settings = QAction("Настройки", self)
            settings.triggered.connect(self.open_settings_of_tray)

            show_action = QAction("Развернуть", self)
            show_action.triggered.connect(self.show)

            hide_action = QAction("Свернуть", self)
            hide_action.triggered.connect(self.hide)

            quit_action = QAction("Закрыть", self)
            quit_action.triggered.connect(self.close_app)

            self.menu_tray = QMenu()
            self.menu_tray.addAction(check_micro)
            self.menu_tray.addAction(settings)
            self.menu_tray.addAction(show_action)
            self.menu_tray.addAction(hide_action)
            self.menu_tray.addAction(quit_action)
            self.tray_icon.setContextMenu(self.menu_tray)
            self.tray_icon.activated.connect(self.on_tray_icon_activated)
            self.tray_icon.show()

            self.init_file_watcher()
            self.load_existing_logs()

            self.timer = QTimer()
            self.timer.timeout.connect(self.check_log)
            self.timer.start(1000)

        except Exception as e:
            debug_logger.error(f"Ошибка при инициализации GUI: {e}")

    def hide_layout(self, layout):
        """Скрывает все виджеты в layout"""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().hide()

    def show_layout(self, layout):
        """Показывает все виджеты в layout"""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().show()

    def _setup_compact_toolbar(self):
        """Инициализация компактной панели с иконками"""
        self.compact_layout = QHBoxLayout()
        self.compact_layout.setContentsMargins(0, 0, 0, 10)
        self.compact_layout.setSpacing(10)

        while self.compact_layout.count():
            item = self.compact_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.compact_layout.addStretch()

        self.left_spacer = QSpacerItem(1, 40, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.compact_layout.addSpacerItem(self.left_spacer)

        buttons_data = [
            (self.icon_close_path, "Закрыть", self.hide_widget),
            (self.icon_settings_path, "Настройки", self.open_main_settings),
            (self.icon_shortcut_path, "Ваши ярлыки", self.open_folder_shortcuts),
            (self.icon_commands_path, "Ваши команды", self.open_commands_settings),
            (self.icon_other_path, "Прочее", self.other_options),
            (self.icon_guide_path, "Обучение", self.guide_options),
            (self.icon_power_path, "Старт ассистента", self.start_assist_toggle),
            (self.icon_widget_path, "Открыть виджет", self.open_widget),
        ]

        self.btn_svg_list = []

        for svg_path, tooltip, callback in buttons_data:
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            btn.setVisible(False)

            svg_widget = QSvgWidget(svg_path, btn)
            svg_widget.setFixedSize(30, 30)
            svg_widget.move(5, 5)
            svg_widget.setStyleSheet("background: transparent;")
            self.style_manager.apply_color_svg(svg_widget, strength=0.90)

            self.btn_svg_list.append({'button': btn, 'svg': svg_widget})

            self.compact_layout.addWidget(btn)

        self.right_spacer = QSpacerItem(1, 40, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.compact_layout.addSpacerItem(self.right_spacer)
        self.compact_layout.addStretch()

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

    def apply_styles(self):
        """Применяет все стили к окну"""
        try:
            self.styles = self.style_manager.load_styles()
            # Применение к конкретным виджетам
            self.style_manager.apply_to_widget(self.label_version, 'label_version')
            self.style_manager.apply_to_widget(self.label_message, 'label_message')
            self.style_manager.apply_to_widget(self.update_label, 'update_label')

            self.style_manager.apply_progressbar(key="QPushButton", widget=self.progress_load, style="parts")
            # Применение к SVG
            self.style_manager.apply_color_svg(self.svg_image, strength=0.95)
            self.style_manager.apply_color_svg(self.settings_svg, strength=0.90)
            self.style_manager.apply_color_svg(self.shortcut_svg, strength=0.90)
            self.style_manager.apply_color_svg(self.commands_svg, strength=0.90)
            self.style_manager.apply_color_svg(self.guide_svg, strength=0.90)
            self.style_manager.apply_color_svg(self.other_svg, strength=0.90)
            self.style_manager.apply_color_svg(self.power_svg, strength=0.90)
            self.style_manager.apply_color_svg(self.widget_svg, strength=0.90)
            self.style_manager.apply_color_svg(self.icon_svg, strength=0.95)

            # Применение общего стиля окна
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
            self.apply_menu_styles(self.menu_tray)
        except Exception as e:
            debug_logger.error(f"Ошибка в методе apply_styles: {e}")

    def apply_menu_styles(self, menu: QMenu):
        """Применяет стили из self.styles к QMenu"""
        if not hasattr(self, 'styles') or not self.styles:
            return

        menu_style = ""
        for widget_name, styles in self.styles.items():
            if widget_name.startswith("QMenu"):
                menu_style += f"{widget_name} {{\n"
                for prop, value in styles.items():
                    menu_style += f"    {prop}: {value};\n"
                menu_style += "}\n"

        if menu_style.strip():
            menu.setStyleSheet(menu_style)

    def update_colors(self):
        self.styles = self.style_manager.load_styles()
        for data in self.btn_svg_list:  # Итерируемся по списку
            self.style_manager.apply_color_svg(data['svg'], strength=0.90)
        for data in self.svg_settings_list:
            self.style_manager.apply_color_svg(data["svg"], strength=0.90)

    def show_notification_message(self, message):
        try:
            # Проверяем, действительно ли окно скрыто/свёрнуто
            is_window_hidden = self.isMinimized() or not self.isVisible()

            toast = ToastNotification(
                parent=None if is_window_hidden else self,
                message=message,
                timeout=4000
            )
            toast.show()
        except Exception as e:
            debug_logger.error(f"Ошибка при показе всплывающего уведомления: {e}")

    def show_message(self, text, title="Уведомление", message_type="info", buttons=QMessageBox.Ok):
        try:
            message = SimpleNotice(
                parent=self,
                message=text,
                title=title,
                message_type=message_type,
                buttons=buttons
            )
            return message.exec_()
        except Exception as e:
            debug_logger.error(f"Ошибка при показе уведомления(оконного): {e}")
            # В случае ошибки тоже нужно что-то вернуть, например, QDialog.Rejected или None
            return QDialog.Rejected  # или return None

    def keyPressEvent(self, event):
        """Сворачивает основное окно в трей по нажатию на Esc"""
        if event.key() == Qt.Key_Escape:
            if self.mutable_panel.isVisible():
                self.hide_widget()
                event.accept()
            else:
                self.custom_hide()
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

    def open_update_app(self, event):
        """Запускает скрипт для установки обновления при клике на текст."""
        try:
            self.update_app(type_version=self.type_version)
        except Exception as e:
            debug_logger.error(f"Ошибка при запуске программы обновления: {e}")

#  тут исправлена логика обработки ручной проверки
    @pyqtSlot()
    def update_answer(self, event):
        """Реакция бота на отсутствие обновления"""
        try:
            self.is_manual_check = True  # Устанавливаем флаг ручной проверки
            self.check_update_app()
        except Exception as e:
            debug_logger.error(f"Ошибка при запуске программы обновления: {e}")

    def handle_update_status(self, is_success, status_text):
        """Обрабатывает результат проверки обновлений"""
        if not self.is_manual_check:  # Пропускаем реакцию для автоматических проверок
            return

        # Реагируем только если это ручная проверка
        if status_text == "Установлена последняя версия":
            update_button = self.audio_paths.get('update_button')
            thread_react_detail(update_button)
        elif status_text == "Доступно обновление":
            pass
        elif not is_success:
            error = self.audio_paths.get('error_file')
            thread_react_detail(error)

        self.is_manual_check = False

    def toggle_update_button(self):
        """
        Метод для отображения или скрытия кнопки "Установить обновление"
        """
        if self.update_label.text() == "Доступно обновление":
            self.update_btn.show()
        else:
            self.update_btn.hide()

    def update_complete(self):
        download_dir = get_path("update")
        temp_dir = get_path("update_pack")

        # Создаём папки, если их нет
        os.makedirs(download_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        # Удаление всех .zip файлов в папке update
        for old_file in os.listdir(download_dir):
            old_path = os.path.join(download_dir, old_file)
            if os.path.isfile(old_path) and old_file.endswith('.zip'):
                try:
                    os.remove(old_path)
                    debug_logger.info(f"Удалён старый .zip файл: {old_path}")
                except Exception as e:
                    debug_logger.error(f"Не удалось удалить файл {old_path}: {e}")

        # Очистка папки update_pack (рекурсивно)
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                        debug_logger.info(f"Файл удален: {item_path}")
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        debug_logger.info(f"Папка удалена рекурсивно: {item_path}")
                except Exception as e:
                    debug_logger.error(f"Не удалось удалить {item_path}. Ошибка: {e}")
        else:
            debug_logger.info(f"Папка не существует: {temp_dir}")

    def animation_start_load(self):
        progress_signal.start_progress.emit()
        self.progress_load.show()
        self.progress_load.startAnimation()

    def animation_stop_load(self):
        progress_signal.stop_progress.emit()
        self.progress_load.hide()
        self.progress_load.stopAnimation()

    def swap_update_file(self):
        try:
            subprocess.Popen([get_path("swap-updater.exe")], shell=True)
            debug_logger.info("swap-updater.exe успешно запущен")
        except Exception as e:
            debug_logger.error(f"Ошибка при запуске swap-updater.exe: {e}")

    def check_update_app(self):
        """Проверяет обновления"""
        self.animation_start_load()
        progress_signal.start_progress.emit()
        try:
            self.toggle_update_button()
            self.update_label.hide()

            self.thread = VersionCheckThread()
            self.thread.version_checked.connect(self.handle_version_check)
            self.thread.check_failed.connect(self.handle_check_failed)
            self.thread.start()

        except Exception as e:
            self.animation_stop_load()
            logger.error(f"Неожиданная ошибка")
            debug_logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
            self.update_label.show()
            self.update_label.setText("Ошибка обновления")
            QTimer.singleShot(2000, lambda: self.check_update_app())

    def handle_version_check(self, stable_version, exp_version):
        # Обработка полученных версий
        new_version = exp_version if self.beta_version else stable_version
        latest_version = version.parse(new_version)
        current_ver = version.parse(self.version)

        type_version = "exp" if self.beta_version else "stable"

        load_changelog()
        self.changelog_file_path = get_path('update', 'changelog.md')

        if latest_version > current_ver:
            self.download_thread = DownloadThread(type_version)
            self.download_thread.download_complete.connect(self.handle_download_complete)
            self.download_thread.finished.connect(self.animation_stop_load)
            self.download_thread.start()
            self.toggle_update_button()
        else:
            self.animation_stop_load()
            self.update_label.show()
            self.update_label.setText("Установлена последняя версия")
            self.toggle_update_button()
            self.update_checked.emit(True, "Установлена последняя версия")
            self.swap_update_file()
            QTimer.singleShot(2000, lambda: self.update_complete())

    def handle_check_failed(self):
        self.animation_stop_load()
        self.update_label.show()
        self.update_label.setText("Ошибка соединения")
        QTimer.singleShot(2000, self.check_update_app)

    def handle_download_complete(self, file_path, success=True, skipped=False, error=None):
        self.animation_stop_load()
        self.update_label.show()
        self.update_label.setText("Доступно обновление")
        self.toggle_update_button()
        try:
            if success:
                self.type_version = "exp" if "exp_" in os.path.basename(file_path).lower() else "stable"
                version = self.extract_version_simple(file_path)
                self.show_notification_message(f"Доступно обновление (v.{version})")
                if skipped:
                    self.show_notification_message("Сейчас будет установлена новая версия")
                    debug_logger.info(f"[SKIP] Файл уже существует")
                    self.open_window_and_update()
                else:
                    debug_logger.info(f"[OK] Новый файл загружен")
            else:
                debug_logger.error(f"[ERROR] Не удалось скачать: {error}")
        except Exception as e:
            debug_logger.error(f"Ошибка handle_download_complete: {str(e)}", exc_info=True)

    def extract_version_simple(self, filename):
        parts = filename.split('_')
        if len(parts) >= 3:
            return parts[-1].replace('.zip', '')
        return "-.-.-"

    def open_window_and_update(self):
        """Обработка действия, если апдейт уже был скачан (активация окна)"""
        if not self.isVisible():
            self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()
        QTimer.singleShot(500, lambda: self.update_app(type_version=self.type_version))

    # def show_update_notice(self, version):
    #     """Показ уведомления о новой версии"""
    #     if not self.isVisible():  # Если окно скрыто в трее
    #         pass
    #     else:
    #         # Если окно видимо - показываем обычный диалог
    #         self.show_popup(version)
    #
    # def show_popup(self, version):
    #     """Кастомное окно обновления"""
    #     dialog = QDialog(self)
    #     dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
    #     dialog.setFixedSize(450, 200)
    #     screen_geometry = QApplication.primaryScreen().availableGeometry()
    #     dialog.move(
    #         screen_geometry.center() - dialog.rect().center()
    #     )
    #
    #     # Основной контейнер с рамкой
    #     container = QWidget(dialog)
    #     container.setObjectName("WindowContainer")
    #     container.setGeometry(0, 0, dialog.width(), dialog.height())
    #
    #     # Заголовок с крестиком
    #     title_bar = QWidget(container)
    #     title_bar.setObjectName("TitleBar")
    #     title_bar.setGeometry(1, 1, dialog.width() - 2, 35)
    #     title_layout = QHBoxLayout(title_bar)
    #     title_layout.setContentsMargins(10, 5, 10, 5)
    #
    #     title_label = QLabel("Доступно обновление")
    #     title_label.setStyleSheet("background: transparent;")
    #     title_layout.addWidget(title_label)
    #     title_layout.addStretch()
    #
    #     close_btn = QPushButton("✕")
    #     close_btn.setFixedSize(25, 25)
    #     close_btn.setObjectName("CloseButton")
    #     close_btn.clicked.connect(dialog.reject)
    #     title_layout.addWidget(close_btn)
    #
    #     # Основное содержимое
    #     content_widget = QWidget(container)
    #     content_widget.setGeometry(1, 36, dialog.width() - 2, dialog.height() - 37)
    #
    #     # Вертикальный layout
    #     layout = QVBoxLayout(content_widget)
    #     layout.setContentsMargins(10, 10, 10, 10)
    #
    #     # Текст сообщения
    #     text_label = QLabel(
    #         f"<b>Доступна новая версия\n{version}</b>"
    #     )
    #     text_label.setStyleSheet("background: transparent;")
    #     text_label.setAlignment(Qt.AlignCenter)
    #     text_label.setWordWrap(True)
    #     layout.addWidget(text_label)
    #
    #     # Чекбокс
    #     checkbox = QCheckBox("Больше не показывать")
    #     checkbox.setStyleSheet("background: transparent;")
    #     layout.addWidget(checkbox, 0, Qt.AlignLeft)
    #
    #     button_layout = QHBoxLayout()
    #     button_layout.setSpacing(10)
    #
    #     changes_btn = QPushButton("Список изменений")
    #     install_btn = QPushButton("Установить")
    #     later_btn = QPushButton("Позже")
    #
    #     # Настройка кнопок (одинаковая ширина и высота)
    #     for btn in [changes_btn, install_btn, later_btn]:
    #         btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    #         btn.setMinimumHeight(30)
    #
    #     # Добавляем кнопки в горизонтальный layout
    #     button_layout.addWidget(changes_btn)
    #     button_layout.addWidget(install_btn)
    #     button_layout.addWidget(later_btn)
    #
    #     # Вставляем горизонтальный layout в основной вертикальный
    #     layout.addLayout(button_layout)
    #
    #     # Обработчики
    #     def on_changes():
    #         self.changelog_window(None)
    #
    #     def on_install():
    #         self.update_app(type_version=self.type_version)
    #         if checkbox.isChecked():
    #             self.show_upd_msg = False
    #             self.save_settings()
    #         dialog.accept()
    #
    #     def on_later():
    #         if checkbox.isChecked():
    #             self.show_upd_msg = False
    #             self.save_settings()
    #         dialog.reject()
    #
    #     changes_btn.clicked.connect(on_changes)
    #     install_btn.clicked.connect(on_install)
    #     later_btn.clicked.connect(on_later)
    #
    #     # Позиционирование
    #     if self.parent():
    #         dialog.move(
    #             self.parent().geometry().center() - dialog.rect().center()
    #         )
    #     winsound.MessageBeep(winsound.MB_ICONASTERISK)
    #     dialog.exec_()

    def init_logger(self):
        """Инициализация логгера."""
        # Используем ваш конфиг логов
        self.logger = logging.getLogger("assistant")

    def init_file_watcher(self):
        """Инициализация FileSystemWatcher для отслеживания изменений файла логов."""
        self.file_watcher = QFileSystemWatcher([self.log_file_path])
        self.file_watcher.fileChanged.connect(self.update_logs)

    def _check_log_file_size(self, max_lines=100):
        """Проверяет, превышает ли файл логов max_lines строк. Если да — очищает его."""
        try:
            if not os.path.exists(self.log_file_path):
                return

            with open(self.log_file_path, "r", encoding="utf-8-sig", errors="replace") as file:
                lines = file.readlines()

            if len(lines) > max_lines:
                # Очищаем файл и оставляем только последние 10 строк
                with open(self.log_file_path, "w", encoding="utf-8") as file:
                    file.writelines(lines[-10:])
                self.log_area.clear()  # Очищаем QTextEdit
                self.last_position = 0  # Сбрасываем позицию чтения
                self.logger.info("Файл логов превысил лимит, очищен.")
        except Exception as e:
            self.logger.error(f"Ошибка при проверке размера логов: {e}")

    def load_existing_logs(self):
        """Загрузка всех записей из файла логов при запуске."""
        try:
            if not os.path.exists(self.log_file_path):
                self.logger.info("Файл логов не найден. Создаем новый.")
                with open(self.log_file_path, "w", encoding="utf-8"):
                    pass  # Создаем пустой файл
            else:
                self._check_log_file_size()  # Проверяем и чистим, если нужно

            with open(self.log_file_path, "r", encoding="utf-8-sig", errors="replace") as file:
                existing_logs = file.read()
                self.log_area.setPlainText(existing_logs)
                self.last_position = file.tell()
        except Exception as e:
            self.logger.error(f"Ошибка при чтении файла логов: {e}")
            self.log_area.append(f"Ошибка при чтении файла логов: {e}")

    def check_log(self):
        """Проверка файла на наличие новых данных."""
        try:
            if not os.path.exists(self.log_file_path):
                self.logger.warning("Файл логов не найден. Пытаемся переподключиться...")
                self.file_watcher.removePath(self.log_file_path)
                self.file_watcher.addPath(self.log_file_path)
                return

            self._check_log_file_size()  # Проверяем, не превышен ли лимит

            with open(self.log_file_path, "r", encoding="utf-8-sig", errors="replace") as file:
                file.seek(self.last_position)
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

    def update_logs(self):
        """Обновление логов при изменении файла."""
        self.check_log()

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

    def close_app(self):
        """Закрытие приложения."""
        if self.is_assistant_running:
            self.stop_assist()
        qApp.quit()

    def reload_commands(self):
        self.load_commands()

    def load_commands(self):
        """Загружает команды из JSON-файла."""
        file_path = get_path('user_settings', 'commands.json')
        try:
            if not os.path.exists(file_path):
                logger.info(f"Файл {file_path} не найден.")
                debug_logger.debug(f"Файл {file_path} не найден.")
                return {}

            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл {file_path} содержит некорректный JSON.")
            debug_logger.error(f"Ошибка: файл {file_path} содержит некорректный JSON.")
            return {}
        except Exception as e:
            logger.error(f"Ошибка при загрузке команд из файла {file_path}: {e}")
            debug_logger.error(f"Ошибка при загрузке команд из файла {file_path}: {e}")
            return {}

    def save_commands(self):
        """Централизованное сохранение команд"""
        try:
            path = get_path('user_settings', 'commands.json')
            with open(path, 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=4)

        except Exception as e:
            logger.error(f"Ошибка сохранения команд: {e}")

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
            "run_updater": self.run_updater,
            "minimize_to_tray": self.is_min_tray,
            "start_win": self.toggle_start,
            "is_widget": self.is_widget,
            "input_device_id": self.input_device_id,
            "input_device_name": self.input_device_name
        }
        try:
            # Проверяем, существует ли папка user_settings
            os.makedirs(os.path.dirname(self.settings_file_path), exist_ok=True)

            # Сохраняем настройки в файл
            with open(self.settings_file_path, 'w', encoding='utf-8') as file:
                json.dump(settings_data, file, ensure_ascii=False, indent=4)

            if self.run_updater:
                value = "prod"
            else:
                value = "dev"
            set_config_value("app", "build", f"{value}")

            self.show_notification_message("Настройки сохранены!")
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
                "steam_path": "",
                "is_censored": True,
                "volume_assist": 0.2,
                "run_updater": True,
                "minimize_to_tray": True,
                "start_win": True,
                "is_widget": True,
                "input_device_id": None,
                "input_device_name": None
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
                self.hide()
            else:
                screen_geometry = self.screen().availableGeometry()
                self.move(
                    (screen_geometry.width() - self.width()) // 2,
                    (screen_geometry.height() - self.height()) // 2
                )
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
        """Обработка закрытия окна"""
        self.close_child_windows.emit()

        if self.is_assistant_running:
            self.stop_assist()
        event.accept()

    def on_shutdown(self):
        try:
            self.force_close()
        except Exception as e:
            debug_logger.error(f"Ошибка при закрытии приложения: {e}")

    def force_close(self):
        """Принудительное закрытие, игнорируя все подтверждения"""
        self.close()

        # Гарантированное завершение через 100 мс
        QTimer.singleShot(100, lambda: [
            QApplication.closeAllWindows(),
            QApplication.quit()
        ])

    def cleanup_before_exit(self):
        """Подготовка к выходу"""
        if hasattr(self, 'splash') and self.splash.check_thread:
            self.splash.check_thread.quit()
            self.splash.check_thread.wait(1000)
            self.close()

    def handle_close_confirmation(self, confirmed, event, dialog):
        """Обрабатывает ответ пользователя"""
        dialog.close()
        if confirmed:
            self.stop_assist()
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

    def stop_assist(self, reaction=True):
        """Остановка ассистента"""
        self.is_assistant_running = False
        self.start_button.setText("Старт ассистента")
        self.log_area.append("Ассистент остановлен...")
        if reaction:
            audio_paths = get_audio_paths(self.speaker)
            close_assist_folder = audio_paths.get('close_assist_folder')
            react(close_assist_folder)

        # Безопасная остановка потока
        if hasattr(self, 'assistant_thread') and self.assistant_thread is not None:
            try:
                if self.assistant_thread.is_alive() and self.assistant_thread != threading.current_thread():
                    self.assistant_thread.join(timeout=1.0)  # Уменьшаем таймаут
                    if self.assistant_thread.is_alive():
                        debug_logger.warning("Поток ассистента не завершился в течение таймаута")
            except Exception as e:
                debug_logger.error(f"Ошибка при остановке потока: {e}")
            finally:
                self.assistant_thread = None

        # Очистка аудиоресурсов
        self.cleanup_audio_resources()

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
        name_mentioned_time = None  # Время последнего упоминания имени ассистента
        name_mentioned = False  # Флаг, что имя было упомянуто
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

                # Сбрасываем флаг упоминания имени, если прошло более 30 секунд
                if name_mentioned and (current_time - name_mentioned_time) > 30:
                    name_mentioned = False
                    name_mentioned_time = None
                    logger.info("Сброс флага упоминания имени (30 секунд)")
                    debug_logger.info("Сброс флага упоминания имени (30 секунд)")

                if not self.is_assistant_running:
                    break

                # Обновляем время последней активности при получении текста
                last_activity_time = current_time

                # Проверка памяти и цензуры (без изменений)
                if not self.check_memory_usage(self.MEMORY_LIMIT_MB):
                    logger.error("Превышен лимит памяти")
                    debug_logger.error("Превышен лимит памяти")
                    self.stop_assist()
                    self.show_notification_message("Превышен лимит памяти, бот остановлен.")
                    break

                if any(keyword in text for keyword in ['сук', 'суч', 'пизд', 'ебан', 'ебат', 'ёбан',
                                                       'нах', 'хуй', 'блять', 'блядь', 'ебу', 'епта',
                                                       'ёпта', 'гандон', 'пидор', 'пидар', "хуё", "хуя",
                                                       "хую", "хуе", "залуп", "залупа", "пиздюк",
                                                       "ебанут", "ебарь", "ебанат", "еблан", "ебло",
                                                       "еблив", "ебуч", "ёбыр", "заеб", "наеб", "объеб",
                                                       "подъеб", "разъеб", "съеб"]):
                    self.censor_counter()

                if self.is_censored and any(
                        keyword in text for keyword in ['сук', 'суч', 'пизд', 'ебан', 'ебат', 'ёбан',
                                                        'нах', 'хуй', 'блять', 'блядь', 'ебу', 'епта',
                                                        'ёпта', 'гандон', 'пидор', 'пидар', "хуё", "хуя",
                                                        "хую", "хуе", "залуп", "залупа", "пиздюк",
                                                        "ебанут", "ебарь", "ебанат", "еблан", "ебло",
                                                        "еблив", "ебуч", "ёбыр", "заеб", "наеб", "объеб",
                                                        "подъеб", "разъеб", "съеб"]):
                    censored_folder = self.audio_paths.get('censored_folder')
                    thread_react(censored_folder)
                    continue

                # Проверка на упоминание имени ассистента (одно слово)
                words = text.split()
                if len(words) <= 2 and any(
                        name.lower() in words[0].lower()
                        for name in [self.assistant_name, self.assist_name2, self.assist_name3]):
                    echo_folder = self.audio_paths.get('echo_folder')
                    if echo_folder:
                        thread_react(echo_folder)
                    name_mentioned = True
                    name_mentioned_time = current_time
                    continue

                # Проверка на наличие имени ассистента в тексте или флаг упоминания
                has_assistant_name = (self.assistant_name in text or
                                      self.assist_name2 in text or
                                      self.assist_name3 in text or
                                      name_mentioned)
                # Режим уточнения команды (если предыдущая попытка не удалась)
                if last_unrecognized_command:
                    if text:
                        # Обновляем время последней активности при обработке команды
                        last_activity_time = current_time
                        # Проверяем, содержит ли текст только кириллические символы (исключаем английскую речь)
                        # if any(cyr_char in text.lower() for cyr_char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
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
                            'панел': (self._open_widget_signal, self._close_widget_signal),
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
                        if not matched_special and not matched_keyword:
                            what_folder = self.audio_paths.get('what_folder')
                            if what_folder:
                                thread_react(what_folder)

                if has_assistant_name:
                    reaction_triggered = False
                    # Системные команды (без изменений)
                    if 'выключи комп' in text:
                        shutdown_windows()
                        logger.info("shutdown")
                        continue
                    elif 'перезагрузить комп' in text:
                        restart_windows()
                        logger.info("restart")
                        continue
                    action_keywords = ['откр', 'закр', 'вкл', 'выкл', 'откл', 'запус',
                                       'отруб', 'выруб']
                    action = next((kw for kw in action_keywords if kw in text), None)

                    # Проверяем, есть ли в тексте слова-действия
                    has_action_words = any(kw in text.lower() for kw in action_keywords)

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

                        # Определяем тип действия
                        action_type = None
                        if any(kw in command for kw in ['запус', 'откр', 'вкл', 'вруб']):
                            action_type = 'open'
                        elif any(kw in command for kw in ['закр', 'выкл', 'выруб', 'отруб', 'откл']):
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
                            elif 'панел' in command:
                                if action_type == 'open':
                                    self._open_widget_signal()
                                elif action_type == 'close':
                                    self._close_widget_signal()
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
                            # Если есть имя ассистента, но нет команды или непонятная команда
                            if (self.assistant_name in command or
                                    self.assist_name2 in command or
                                    self.assist_name3 in command or
                                    name_mentioned):

                                # Реагируем только если есть слова-действия, но команда не распознана
                                if has_action_words:
                                    what_folder = self.audio_paths.get('what_folder')
                                    if what_folder:
                                        thread_react(what_folder)
                                    reaction_triggered = True
                                else:
                                    if any(word in command for word in ["найди", "поищи", "посмотри", "гугли"]):
                                        search_yandex(command, self.assistant_name,
                                                      self.assist_name2,
                                                      self.assist_name3)
                                        approve_folder = self.audio_paths.get('approve_folder')
                                        thread_react(approve_folder)
                                    elif any(word in command for word in ["фулл скрин", "весь экран", "сфотк"]):
                                        self.capture_fullscreen()
                                    elif any(word in command for word in ["скрин", "област"]):
                                        self.capture_area()
                                    # elif 'игровой режим' in command:
                                    #     if action_type == 'open':
                                    #         self.start_game_mode()
                                    #     else:
                                    #         self.stop_game_mode()
                                    else:
                                        # Если просто разговор, а не команда - не реагируем вопросом
                                        pass

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
                              "warning")

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

    def restart_bot(self):
        self.stop_assist(reaction=False)
        QTimer.singleShot(3000, lambda: self.run_assist())

    def initialize_audio(self):
        """Инициализация моделей и аудиопотока через sounddevice."""
        self.cleanup_audio_resources()
        logger.info("Загрузка моделей для распознавания...")
        debug_logger.debug("Загрузка моделей для распознавания...")

        model_path_ru = get_path("bin", "model_ru")
        model_path_en = get_path("bin", "model_en")
        debug_logger.debug(f"Загружена модель RU - {model_path_ru}")
        debug_logger.debug(f"Загружена модель EN - {model_path_en}")

        try:
            self.model_ru = Model(model_path_ru)
            self.model_en = Model(model_path_en)
            logger.info("Модели успешно загружены.")
            debug_logger.info("Модели успешно загружены.")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}. Возможно путь содержит кириллицу.")
            debug_logger.error(f"Ошибка при загрузке модели: {e}", exc_info=True)
            return False

        try:
            # Инициализация распознавателей
            self.rec_ru = KaldiRecognizer(self.model_ru, 16000)
            self.rec_en = KaldiRecognizer(self.model_en, 16000)

            target_id = self.get_microphone_id(self.input_device_name)
            if target_id is None:
                logger.warning("Не удалось определить микрофон. Используем устройство по умолчанию.")
                target_id = sd.default.device[0] if sd.default.device[0] < len(sd.query_devices()) else None

            if target_id is None:
                raise RuntimeError("Нет доступных входных устройств")

            try:
                self.audio_stream = sd.InputStream(
                    samplerate=16000,
                    channels=1,
                    dtype='int16',
                    blocksize=512,
                    device=target_id,
                    callback=self.audio_callback
                )
                self.audio_stream.start()
                self.input_device_id = target_id  # обновляем ID
                device_name = sd.query_devices(target_id)['name']
                self.input_device_name = device_name  # фиксируем имя
                debug_logger.info(f"Аудиопоток запущен: '{device_name}' (ID={target_id})")
            except Exception as e:
                debug_logger.error(f"Не удалось открыть выбранное устройство (ID={target_id}): {e}")
                # Fallback: попробовать без указания устройства (по умолчанию)
                try:
                    self.audio_stream = sd.InputStream(
                        samplerate=16000,
                        channels=1,
                        dtype='int16',
                        blocksize=512,
                        callback=self.audio_callback
                    )
                    self.audio_stream.start()
                    fallback_id = sd.default.device[0]
                    fallback_name = sd.query_devices(fallback_id)['name']
                    self.input_device_id = fallback_id
                    self.input_device_name = fallback_name
                    debug_logger.warning(f"Используется устройство по умолчанию: '{fallback_name}'")
                except Exception as e2:
                    debug_logger.error("Не удалось запустить ни одно устройство.", exc_info=True)
                    raise e2

            # ✅ Успешно запущено
            self.microphone_available = True
            self.last_audio_time = time.time()  # начальное значение для watchdog
            return True

        except Exception as e:
            debug_logger.error(f"Критическая ошибка при инициализации аудио: {e}", exc_info=True)
            return False

    def get_microphone_id(self, preferred_name=None):
        """Возвращает ID микрофона по имени"""
        try:
            devices = sd.query_devices()
            default_in = sd.default.device[0]
            candidates = []
            seen = set()

            for dev in devices:
                idx, name, ch = dev['index'], dev.get('name', ''), dev.get('max_input_channels', 0)
                if ch <= 0 or not name:
                    continue

                # Фильтр: системные, дубли, нежелательные
                clean = name.split('(')[0].strip()
                lower_name = name.lower()
                if (clean in seen or
                        any(kw in lower_name for kw in ['mapper', 'primary', 'wave', 'default', 'communications'])):
                    continue
                seen.add(clean)

                # Приоритет API: WASAPI > ASIO > остальные
                api_name = sd.query_hostapis(dev['hostapi'])['name'].lower()
                priority = {'wasapi': 3, 'asio': 2}.get(api_name, 1)

                try:
                    with sd.InputStream(device=idx, channels=1, samplerate=16000, blocksize=512):
                        candidates.append((idx, priority, preferred_name and preferred_name.lower() in lower_name))
                except Exception:
                    continue

            # Сортировка: совпадение по имени → приоритет API → индекс
            if candidates:
                best = max(candidates, key=lambda x: (x[2], x[1], -x[0]))
                return best[0]

            return default_in  # fallback

        except Exception as e:
            debug_logger.warning(f"Ошибка выбора микрофона: {e}")
            return sd.default.device[0]  # двойной fallback

    def audio_callback(self, indata, frames, time_info, status):
        """
        :param time_info: Временные метки от PortAudio
        """
        if status:
            debug_logger.warning(f"⚠️ Статус аудио: {status}")
            if any(keyword in str(status).lower() for keyword in ['overrun', 'underrun']):
                pass  # Будет обработано по тишине
            else:
                return

        if len(indata) == 0:
            return

        # === АНАЛИЗ ГРОМКОСТИ ===
        try:
            audio_data = np.frombuffer(indata, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            is_silent = rms < 20

            if not is_silent:
                self.last_audio_time = time.time()

        except Exception as e:
            debug_logger.error(f"Ошибка при анализе громкости: {e}")

        data = indata.tobytes()
        ru_text = ""
        en_text = ""

        try:
            if self.rec_ru.AcceptWaveform(data):
                result = json.loads(self.rec_ru.Result())
                ru_text = result.get("text", "").strip().lower()

            if self.rec_en.AcceptWaveform(data):
                result = json.loads(self.rec_en.Result())
                temp_en = result.get("text", "").strip().lower()
                if temp_en and temp_en != "huh":
                    en_text = temp_en

            final_text = ru_text or en_text
            if final_text:
                self.on_final_result(final_text)

        except Exception as e:
            debug_logger.error(f"Ошибка в обработке распознавания: {e}")

    def on_final_result(self, text):
        """Вызывается при распознавании фразы. Логирует и отправляет дальше."""
        logger.info(f"[Распознано] {text}")
        debug_logger.info(f"[Распознано] {text}")

        # Если есть активная очередь (например, get_audio() ждёт), — кладём туда
        if hasattr(self, '_current_queue') and self._current_queue is not None:
            try:
                self._current_queue.put(text)
            except Exception as e:
                logger.error(f"Не удалось положить текст в очередь: {e}")

    def get_audio(self):
        """
        Совместимый интерфейс: возвращает генератор текста.
        Но теперь работает через callback + очередь.
        """
        # Вариант 1: если хочешь оставить yield — используй очередь
        from queue import Queue
        q = Queue()

        # Сохраним ссылку, чтобы можно было выйти
        self.text_queue = q
        self._current_queue = q

        try:
            while self.is_assistant_running:
                try:
                    text = q.get(timeout=1)
                    yield text
                except:
                    continue
        except Exception as e:
            logger.error(f"Ошибка в get_audio: {e}")
        finally:
            if hasattr(self, '_current_queue'):
                del self._current_queue

    # === ПРОВЕРКА МИКРОФОНА ===
    def check_microphone(self):
        """Проверка доступности микрофона через sounddevice"""
        debug_logger.info("Проверка микрофона через sounddevice...")
        try:
            devices = sd.query_devices()
            active_mics = []

            for device in devices:
                if device['max_input_channels'] <= 0:
                    continue

                device_id = device['index']
                name = device['name']

                # Фильтруем системные
                if any(kw in name.lower() for kw in ['mapper', 'primary', 'wave', 'default']):
                    continue

                try:
                    with sd.InputStream(
                            device=device_id,
                            channels=1,
                            samplerate=44100,
                            blocksize=1024
                    ):
                        active_mics.append(device)
                except Exception:
                    continue

            if active_mics:
                debug_logger.info(f"Найдено рабочих микрофонов: {len(active_mics)}")
                self.microphone_available = True
                return True
            else:
                logger.info("Нет доступных микрофонов.")
                self.microphone_available = False
                return False

        except Exception as e:
            debug_logger.error(f"Ошибка проверки микрофона: {e}")
            self.microphone_available = False
            return False

    def _check_microphone_wrapper(self):
        try:
            self.check_microphone()
            if self.microphone_available:
                if not self.is_assistant_running:
                    self.show_notification_message(message="Микрофон обнаружен!")
                    self.run_assist()
                    # self.check_micro_btn.hide()
                else:
                    self.show_notification_message(message="Микрофон подключен!")
            else:
                self.show_notification_message(message="Микрофон не найден!")
        except Exception as e:
            logger.error(f"Ошибка в _check_microphone_wrapper: {e}")

    def cleanup_audio_resources(self):
        """Безопасное освобождение аудиоресурсов"""
        try:
            if hasattr(self, 'audio_stream') and self.audio_stream is not None:
                try:
                    if self.audio_stream.active:
                        self.audio_stream.abort()  # быстро остановить
                except Exception as e:
                    debug_logger.error(f"Ошибка при остановке аудиопотока: {e}")
                finally:
                    self.audio_stream = None
                    debug_logger.info("Аудиопоток остановлен и очищен.")
        except Exception as e:
            debug_logger.error(f"Критическая ошибка аудиопотока: {e}", exc_info=True)

    def check_silence_timeout(self):
        """Проверяет, сколько времени прошло с последнего звука"""
        if not self.is_assistant_running or not self.microphone_available:
            return

        if self.last_audio_time is None:
            return  # Ещё не было данных

        silent_duration = time.time() - self.last_audio_time

        if silent_duration > 10.0:  # 10 секунд тишины
            debug_logger.warning(f"🔊 Нет звука более 10 сек ({silent_duration:.1f}s) — перезапуск аудиопотока")
            self.restart_audio_stream()

    def restart_audio_stream(self):
        """Перезапускает только InputStream, не трогая модели и ассистента"""
        debug_logger.info("🔄 Перезапуск аудиопотока...")

        try:
            # Останавливаем старый поток
            if hasattr(self, 'audio_stream') and self.audio_stream is not None:
                if self.audio_stream.active:
                    self.audio_stream.abort()
                self.audio_stream = None
                debug_logger.info("Старый аудиопоток остановлен")

            # Создаём новый — без указания устройства → по умолчанию
            self.audio_stream = sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='int16',
                blocksize=512,
                callback=self.audio_callback
            )
            self.audio_stream.start()

            # Обновляем время активности
            self.last_audio_time = time.time()

            debug_logger.info("✅ Аудиопоток успешно перезапущен (по умолчанию)")

        except Exception as e:
            debug_logger.error(f"❌ Не удалось перезапустить поток: {e}")
            # Можно попробовать повторно через 10 сек
            QTimer.singleShot(10000, self.restart_audio_stream)

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

    def _open_widget_signal(self):
        try:
            gui_signals.open_widget_signal.emit()
        except Exception as e:
            debug_logger.error(f"Ошибка при запуске сигнала виджета: {e}")

    def _close_widget_signal(self):
        try:
            gui_signals.close_widget_signal.emit()
        except Exception as e:
            debug_logger.error(f"Ошибка при запуске сигнала виджета (на закрытие): {e}")

    def open_widget(self):
        QTimer.singleShot(200, self._show_smart_widget)

    def _show_smart_widget(self):
        try:
            # Полная проверка существующего виджета
            widget_exists = (
                    hasattr(self, 'widget_window') and
                    self.widget_window is not None and
                    isinstance(self.widget_window, SmartWidget))

            if widget_exists and self.widget_window.isVisible():
                return  # Виджет уже видим - ничего не делаем

            if widget_exists:
                # Виджет существует, но скрыт - показываем
                self.widget_window.show()
            else:
                # Создаем новый виджет
                self.widget_window = SmartWidget(self)
                self.widget_window.show()

        except Exception as e:
            debug_logger.error(f"Ошибка при открытии виджета: {str(e)}")
            self.show_notification_message(f"Ошибка при открытии виджета: {str(e)}")

    def close_widget(self):
        try:
            if hasattr(self, "widget_window"):
                self.widget_window.close()
                self.show()
                self.hide()
        except Exception as e:
            error_message = self.audio_paths("error_file")
            thread_react_detail(error_message)
            self.show_notification_message(f"Ошибка при закрытии виджета (close_widget): {e}")
            debug_logger.error(f"Ошибка при закрытии виджета (close_widget): {e}")

    def restore_and_hide(self):
        """Показываем окно и сразу скрываем — чтобы оно стало 'живым'"""
        self.move(-2000, -2000)
        self.showNormal()  # Восстанавливаем из минимизации/скрытия
        self.raise_()  # Поднимаем поверх всех
        self.activateWindow()  # Делаем активным
        QTimer.singleShot(50, self.hide)

    def open_folder_shortcuts(self):
        """Обработка нажатия кнопки 'Открыть папку с ярлыками'"""
        folder_path = get_path('user_settings', "links for assist")
        debug_logger.info(f"Открытие папки ярлыков , {folder_path}")

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
        debug_logger.info(f"Открытие папки скриншотов, {folder_path}")

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

    def open_settings_of_tray(self):
        if self.isVisible():
            self.open_main_settings()
        else:
            self.showNormal()
            self.open_main_settings()

    def open_main_settings(self):
        """Открывает панель настроек"""
        try:
            if self.mutable_panel.isVisible() and self._current_panel == 'settings':
                self.hide_widget()
                return

            self._current_panel = 'settings'

            if self.mutable_panel.isVisible():
                # Уже открыто — запускаем анимацию переключения
                self._load_current_panel()
            else:
                self.show_widget()  # Запускаем анимацию открытия

        except Exception as e:
            debug_logger.error(f"Ошибка при открытии настроек: {e}")
            self.show_message("Ошибка", "error")

    def show_widget(self):
        """Открывает панель настроек: сначала сжимаем, потом расширяем с изменяемой панелью"""
        # Анимация сжатия левой панели
        self._load_current_panel()
        self.show_layout(self.compact_layout)
        self.show_compact_buttons()

        self.animation.stop()
        self.animation.setPropertyName(b"maximumWidth")
        self.animation.setStartValue(220)
        self.animation.setEndValue(1)
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.InBack)
        # После сжатия — начинаем расширение с панелью настроек
        self.animation.finished.connect(self._expand_mutable_panel)
        self.animation.start()

    def _expand_mutable_panel(self):
        """Вызывается после сжатия: показываем панель и загружаем нужный контент"""
        self.left_buttons_panel.hide()
        self.animation.finished.disconnect(self._expand_mutable_panel)
        self.mutable_panel.show()

        self.animation.setStartValue(1)
        self.animation.setEndValue(self._get_panel_width())
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        self.animation.start()

    def _clear_mutable_panel(self):
        """Очищает содержимое mutable_panel"""
        while self.mutable_layout.count():
            item = self.mutable_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_current_panel(self):
        """Загружает текущую панель (настройки или прочее)"""
        if self._current_panel == 'settings':
            if self.mutable_panel.isVisible():
                # Если панель уже видна - анимируем переключение
                self._animate_content_switch(self._load_settings_panel)
            else:
                self._load_settings_panel()
        elif self._current_panel == 'other':
            if self.mutable_panel.isVisible():
                # Если панель уже видна - анимируем переключение
                self._animate_content_switch(self._load_other_panel)
            else:
                self._load_other_panel()
        elif self._current_panel == 'guide':
            if self.mutable_panel.isVisible():
                # Если панель уже видна - анимируем переключение
                self._animate_content_switch(self._load_guide_panel)
            else:
                self._load_guide_panel()
        elif self._current_panel == 'commands':
            if self.mutable_panel.isVisible():
                # Если панель уже видна - анимируем переключение
                self._animate_content_switch(self._load_commands_panel)
            else:
                self._load_commands_panel()

    def hide_widget(self):
        """Закрывает панель настроек"""
        # Сброс эффектов
        for item in self.btn_svg_list:
            btn = item['button']
            btn.setGraphicsEffect(None)
            btn.setVisible(False)

        # Сжимаем
        self.animation.stop()
        self.animation.setPropertyName(b"maximumWidth")
        self.animation.setStartValue(self._get_panel_width())
        self.animation.setEndValue(1)
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.InBack)
        self.animation.finished.connect(self._restore_buttons_panel)
        self.animation.start()

    def show_compact_buttons(self):
        for item in self.btn_svg_list:
            btn = item['button']
            btn.setVisible(True)

    def _restore_buttons_panel(self):
        """Восстанавливаем основную панель"""
        try:
            self.animation.finished.disconnect(self._restore_buttons_panel)
        except:
            pass

        self.mutable_panel.hide()
        self.left_buttons_panel.show()

        # Восстанавливаем ширину
        self.animation.setPropertyName(b"maximumWidth")
        self.animation.setStartValue(1)
        self.animation.setEndValue(230)
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        self.animation.start()

    def _animate_content_switch(self, new_content_callback):
        """Анимация смены контента в видимой панели"""
        # Анимация исчезновения текущего контента
        self.animation.stop()
        self.animation.setPropertyName(b"maximumWidth")
        self.animation.setStartValue(400)
        self.animation.setEndValue(1)
        self.animation.setDuration(350)
        self.animation.setEasingCurve(QEasingCurve.InBack)

        # После сжатия - загружаем новый контент и расширяем
        self.animation.finished.connect(lambda: self._expand_after_switch(new_content_callback))
        self.animation.start()

    def _expand_after_switch(self, new_content_callback):
        """Вызывается после сжатия при переключении контента"""
        self.animation.finished.disconnect()

        # Загружаем новый контент
        new_content_callback()

        # Анимация расширения
        self.animation.setStartValue(1)
        self.animation.setEndValue(self._get_panel_width())
        self.animation.setDuration(350)
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        self.animation.start()

    def _get_panel_width(self):
        """Возвращает ширину панели в зависимости от текущего контента"""
        return 500 if self._current_panel == 'commands' else 400

    def _load_settings_panel(self):
        """Инициализация виджетов настроек с SVG на вкладках"""
        if not hasattr(self, 'mutable_layout') or self.mutable_layout is None:
            return
        self.svg_settings_list = []
        self._clear_mutable_panel()

        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsTabs")
        self.tabs.setDocumentMode(True)

        # Создаем виджеты для содержимого вкладок
        main_widget = SettingsWidget(self)
        other_widget = OtherSettingsWidget(self)
        interface_widget = InterfaceWidget(self)

        self.tabs.addTab(main_widget, "")
        self.tabs.addTab(other_widget, "")
        self.tabs.addTab(interface_widget, "")

        tab_bar = self.tabs.tabBar()

        def create_centered_svg_tab(svg_path):
            svg = QSvgWidget(svg_path)
            svg.setFixedSize(32, 32)
            svg.setStyleSheet("background: transparent;")
            self.style_manager.apply_color_svg(svg, strength=0.90)
            self.svg_settings_list.append({"svg": svg})
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(10, 0, 0, 5)
            layout.addStretch()
            layout.addWidget(svg)
            layout.addStretch()
            return container

        tab_bar.setTabButton(0, QTabBar.LeftSide, create_centered_svg_tab(self.icon_settings_path))
        tab_bar.setTabButton(1, QTabBar.LeftSide, create_centered_svg_tab(self.icon_advance_settings_path))
        tab_bar.setTabButton(2, QTabBar.LeftSide, create_centered_svg_tab(self.icon_styles_path))

        self.tabs.setTabToolTip(0, "Основные настройки")
        self.tabs.setTabToolTip(1, "Дополнительные настройки")
        self.tabs.setTabToolTip(2, "Настройки интерфейса")

        self.mutable_layout.addWidget(self.tabs)
        self.mutable_layout.addSpacerItem(QSpacerItem(self._get_panel_width(), 1, QSizePolicy.Fixed, QSizePolicy.Fixed))

        if isinstance(self.tabs.widget(0), SettingsWidget):
            self.tabs.widget(0).voice_changed.connect(self.update_voice)

    def open_commands_settings(self):
        """Открывает встроенную панель 'Ваши Команды'"""
        try:
            if self.mutable_panel.isVisible() and self._current_panel == 'commands':
                self.hide_widget()
                return

            self._current_panel = 'commands'

            if self.mutable_panel.isVisible():
                # Уже открыто — запускаем анимацию переключения
                self._load_current_panel()
            else:
                self.show_widget()  # Запускаем анимацию открытия
        except Exception as e:
            debug_logger.error(f"Ошибка при открытии настроек команд: {e}", exc_info=True)
            self.show_message(f"Ошибка при открытии настроек команд: {str(e)}", "Ошибка", "error")

    def _load_commands_panel(self):
        """Инициализация виджетов настроек с SVG на вкладках"""
        if not hasattr(self, 'mutable_layout') or self.mutable_layout is None:
            return
        self.svg_settings_list = []
        self._clear_mutable_panel()

        self.tabs = QTabWidget()
        self.tabs.setObjectName("CommandsTabs")
        self.tabs.setDocumentMode(True)

        # Создаем виджеты для содержимого вкладок
        new_com_widget = CreateCommandsWidget(self)
        added_com_widget = CommandsWidget(self)
        process_links_widget = ProcessLinksWidget(self)

        self.tabs.addTab(new_com_widget, "")
        self.tabs.addTab(added_com_widget, "")
        self.tabs.addTab(process_links_widget, "")

        tab_bar = self.tabs.tabBar()

        def create_centered_svg_tab(svg_path):
            svg = QSvgWidget(svg_path)
            svg.setFixedSize(32, 32)
            svg.setStyleSheet("background: transparent;")
            self.style_manager.apply_color_svg(svg, strength=0.90)
            self.svg_settings_list.append({"svg": svg})
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(10, 0, 0, 5)
            layout.addStretch()
            layout.addWidget(svg)
            layout.addStretch()
            return container

        tab_bar.setTabButton(0, QTabBar.LeftSide, create_centered_svg_tab(self.icon_create_command_path))
        tab_bar.setTabButton(1, QTabBar.LeftSide, create_centered_svg_tab(self.icon_added_commands_path))
        tab_bar.setTabButton(2, QTabBar.LeftSide, create_centered_svg_tab(self.icon_process_link_path))

        self.tabs.setTabToolTip(0, "Создание новых команд")
        self.tabs.setTabToolTip(1, "Список ваших команд")
        self.tabs.setTabToolTip(2, "Процессы ярлыков")

        self.mutable_layout.addWidget(self.tabs)
        self.mutable_layout.addSpacerItem(QSpacerItem(self._get_panel_width() + 30, 1, QSizePolicy.Fixed, QSizePolicy.Fixed))

    def other_options(self):
        """Открывает встроенную панель 'Прочее'"""
        try:
            if self.mutable_panel.isVisible() and hasattr(self, '_current_panel') and self._current_panel == 'other':
                self.hide_widget()
                return

            self._current_panel = 'other'

            if self.mutable_panel.isVisible():
                self._load_current_panel()
            else:
                self.show_widget()

        except Exception as e:
            debug_logger.error(f"Ошибка при открытии раздела 'Прочее': {e}")
            self.show_message("Ошибка при открытии 'Прочее'", "Ошибка", "error")

    def _load_other_panel(self):
        """Инициализация виджетов настроек (вызывается один раз)"""
        if not hasattr(self, 'mutable_layout') or self.mutable_layout is None:
            return

        self._clear_mutable_panel()

        # Создаём вкладки
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.svg_others_list = []

        # Добавляем вкладки
        self.tabs.addTab(CensorCounterWidget(self), "")
        self.tabs.addTab(CheckUpdateWidget(self), "")
        self.tabs.addTab(DebugLoggerWidget(self), "")
        self.tabs.addTab(RelaxWidget(self), "")

        # Добавляем вкладку для открытия папки
        folder_tab = QWidget()
        self.tabs.addTab(folder_tab, "")

        tab_bar = self.tabs.tabBar()

        def create_centered_svg_tab(svg_path):
            svg = QSvgWidget(svg_path)
            svg.setFixedSize(32, 32)
            svg.setStyleSheet("background: transparent;")
            self.style_manager.apply_color_svg(svg, strength=0.90)
            self.svg_others_list.append({"svg": svg})
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(10, 0, 0, 5)
            layout.addStretch()
            layout.addWidget(svg)
            layout.addStretch()
            return container

        tab_bar.setTabButton(0, QTabBar.LeftSide, create_centered_svg_tab(self.icon_censor_path))
        tab_bar.setTabButton(1, QTabBar.LeftSide, create_centered_svg_tab(self.icon_updates_path))
        tab_bar.setTabButton(2, QTabBar.LeftSide, create_centered_svg_tab(self.icon_logs_path))
        tab_bar.setTabButton(3, QTabBar.LeftSide, create_centered_svg_tab(self.icon_relax_path))
        tab_bar.setTabButton(4, QTabBar.LeftSide, create_centered_svg_tab(self.icon_screenshot_path))

        self.tabs.setTabToolTip(0, "Счетчик цензуры")
        self.tabs.setTabToolTip(1, "Обновления")
        self.tabs.setTabToolTip(2, "Подробные логи")
        self.tabs.setTabToolTip(3, "Релакс?")
        self.tabs.setTabToolTip(4, "Папка скриншотов")

        # Обработчик переключения вкладок
        def on_tab_changed(index):
            if index == 4:  # Если выбрана вкладка "Папка скриншотов"
                self.open_folder_screenshots()
                self.tabs.setCurrentIndex(0)

        self.tabs.currentChanged.connect(on_tab_changed)

        # Добавляем в layout
        self.mutable_layout.addWidget(self.tabs)
        self.spacer = QSpacerItem(self._get_panel_width(), 1, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.mutable_layout.addSpacerItem(self.spacer)

    def guide_options(self):
        """Открывает панель гайдов"""
        try:
            if self.mutable_panel.isVisible() and self._current_panel == 'guide':
                self.hide_widget()
                return

            self._current_panel = 'guide'

            if self.mutable_panel.isVisible():
                self._load_current_panel()
            else:
                self.show_widget()

        except Exception as e:
            debug_logger.error(f"Ошибка при открытии гайдов: {e}")
            self.show_message("Ошибка", "error")

    def _load_guide_panel(self):
        """Загружает интерфейс гайдов в mutable_panel"""
        self._clear_mutable_panel()
        self._current_panel = 'guide'  # Флаг для отслеживания

        self.main = QWidget()
        self.main_layout = QVBoxLayout(self.main)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.spacer = QSpacerItem(self._get_panel_width(), 1, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.main_layout.addSpacerItem(self.spacer)
        # Заголовок
        label = QLabel("🎥 Обучение")
        label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px; background: transparent;")
        self.main_layout.addWidget(label, alignment=Qt.AlignCenter)

        # Кнопки для видео
        path_guides = get_path("bin", "guides")
        videos = [
            ("Создание команд", f"{path_guides}/new_commands.mp4"),
            ("Настройки и опции", f"{path_guides}/settings.mp4"),
        ]

        for title, video_path in videos:
            btn = QPushButton(title)
            btn.clicked.connect(lambda _, p=video_path: self._open_video(p))
            self.main_layout.addWidget(btn)

        # Кнопка "Встроенные команды"
        cmd_btn = QPushButton("Встроенные команды")
        cmd_btn.clicked.connect(self._load_commands_info)
        self.main_layout.addWidget(cmd_btn)
        self.mutable_layout.addWidget(self.main)

    def _open_video(self, video_path):
        full_path = get_path(video_path)
        if os.path.exists(full_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(full_path))
        else:
            debug_logger.error(f"Видео не найдено: {full_path}")
            self.show_message("Видео не найдено", "Ошибка", "error")

    def _load_commands_info(self):
        self._clear_mutable_panel()
        self._current_panel = 'commands'

        sections = [
            ("Формула команды",
             "'Имя ассистента'\n+\n'Открой, запусти, включи'/'закрой выключи'\n+\n'команда, созданная вручную или из списка встроенных'"),
            ("Встроенные команды (открыть/закрыть)",
             "'Пейнт', 'Калькулятор', 'Корзина', 'АппДата', 'Переменные окружения', 'Диспетчер задач', 'Микшер',"
             "'Панель(для вызова виджета)'"),
            ("Прочие команды",
             "'Выключи комп', 'Перезагрузи комп', 'Найди, поищи, загугли', 'Скрин, область', 'Фулл скрин, сфоткай, весь экран'"),
            ("Управление плеером без произношения имени бота", "(Плеер) + (Действие)\n\n" +
             "Пауза, врубай, включи, запусти\n" +
             "Стоп, выключи, отключи, останови\n" +
             "Следующий, дальше, вперед\n" +
             "Предыдущий, назад"),
        ]

        for title, text in sections:
            lbl_title = QLabel(f"<b>{title}</b>")
            lbl_title.setStyleSheet("background: transparent;")
            lbl_text = QLabel(text)
            lbl_text.setWordWrap(True)
            lbl_text.setStyleSheet("margin-left: 10px; margin-bottom: 10px; font-size: 13px; background: transparent;")
            self.mutable_layout.addWidget(lbl_title)
            self.mutable_layout.addWidget(lbl_text)

        back_btn = QPushButton("Назад к гайдам")
        back_btn.clicked.connect(self._load_guide_panel)
        self.mutable_layout.addWidget(back_btn)

    def changelog_window(self, event):
        """Открываем окно с логами изменений"""
        dialog = ChangelogWindow(self)
        dialog.exec_()

    def update_app(self, type_version=None):
        """Обработка нажатия кнопки 'Установить обновление'"""
        dialog = UpdateApp(self, type_version)
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
            self.update_svg_color(self.start_svg, self.color_path)
        else:
            self.update_svg_contrast_color(self.start_svg)

    def check_start_widget(self):
        if self.is_widget:
            self.open_widget()

    def toggle_start_win(self):
        """Переключает состояние и меняет цвет иконки"""
        self.toggle_start = not self.toggle_start

        if self.toggle_start:
            self.add_to_autostart()
            self.update_svg_color(self.start_svg, self.color_path)
        else:
            self.remove_from_autostart()
            self.update_svg_contrast_color(self.start_svg)

    def update_svg_color(self, svg_widget: QSvgWidget, style_file: str) -> None:
        """Обновляет цвет SVG, учитывая градиенты и контрастность"""

        def extract_primary_color(color_value: str) -> str:
            """Извлекает основной цвет (первый цвет градиента или HEX)"""
            if not color_value:
                return "#FFFFFF"

            # Ищем градиент
            gradient_match = re.search(r"qlineargradient\([^)]+stop:0\s+(#[0-9a-fA-F]+)", color_value)
            if gradient_match:
                return gradient_match.group(1)

            # Ищем обычный HEX-цвет
            hex_match = re.search(r"#[0-9a-fA-F]{3,6}", color_value)
            return hex_match.group(0) if hex_match else "#FFFFFF"

        try:
            # 1. Загружаем стили
            with open(style_file) as f:
                styles = json.load(f)

            # 2. Извлекаем цвета с поддержкой градиентов
            border_color = extract_primary_color(
                styles.get("TitleBar", {}).get("border-bottom", "")
            )

            bg_color = extract_primary_color(
                styles.get("QWidget", {}).get("background-color", "")
            )
            base_bg_color = QColor(bg_color)

            # 3. Вычисляем яркость фона (формула восприятия яркости)
            brightness = (0.299 * base_bg_color.red() +
                          0.587 * base_bg_color.green() +
                          0.114 * base_bg_color.blue()) / 255

            # 4. Выбираем контрастный цвет
            final_color = "#369EFF" if brightness > 0.5 else border_color

            # 5. Генерируем SVG с новым цветом
            svg_template = '''<?xml version="1.0" encoding="utf-8"?>
            <svg fill="{color}" width="20px" height="20px" viewBox="0 0 24 24" 
                 xmlns="http://www.w3.org/2000/svg">
                <path d="m9.84 12.663v9.39l-9.84-1.356v-8.034zm0-10.72v9.505h-9.84v-8.145zm14.16 10.72v11.337l-13.082-1.803v-9.534zm0-12.663v11.452h-13.082v-9.649z"/>
            </svg>'''

            svg_widget.load(svg_template.format(color=final_color).encode('utf-8'))

        except Exception as e:
            logger.error(f"Ошибка при обновлении цвета SVG: {e}")
            debug_logger.error(f"Ошибка при обновлении цвета SVG: {e}")
            # Fallback на белый цвет при ошибке
            svg_widget.load(svg_template.format(color="#FFFFFF").encode('utf-8'))

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
            self.show_notification_message(message=f"Программа добавлена в автозапуск")

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
            self.show_notification_message(message=f"Программа удалена из автозапуска")
        except subprocess.CalledProcessError as e:
            if "не существует" not in e.stderr:
                error_msg = f"Ошибка при удалении задачи '{task_name}': {e.stderr}"
                self.show_notification_message(message=f"{error_msg}")
                debug_logger.error(error_msg)
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
        except subprocess.CalledProcessError as e:
            if "не существует" not in e.stderr:
                error_msg = f"Ошибка при проверке задачи '{task_name}': {e.stderr}"
                logger.error(error_msg)
                debug_logger.error(error_msg)
            self.toggle_start = False
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
    def __init__(self, parent=None, type_version="stable"):
        super().__init__(parent)
        self.assistant = parent
        self.type_version = type_version
        self.update_file_path = self.find_update_file()
        self.extract_dir = get_path("update_pack")
        os.makedirs(self.extract_dir, exist_ok=True)

    def main(self):
        if not self.update_file_path:
            debug_logger.error("Не найден файл обновления (*.zip)")
            return

        if not self.extract_archive(self.update_file_path):
            self.assistant.show_notification_message("Не удалось распаковать архив с новой версией")
            return
        debug_logger.info(f"Архив с новой версией распакован по пути {self.extract_dir}")
        self.assistant.show_notification_message("Начинаю установку...")
        QTimer.singleShot(800, lambda: self.start_update())

    def start_update(self):
        try:
            # флаг no-checked для пропуска проверки новой версии в апдейте
            subprocess.Popen([get_path("Update.exe"), "--no-checked"], shell=True)
            debug_logger.info("Update.exe успешно запущен")
        except Exception as e:
            debug_logger.error(f"Ошибка при запуске Update.exe: {e}")

    def find_update_file(self):
        update_dir = get_path("update")
        pattern = f"{self.type_version}_Assistant_*.zip"
        # Ищем самый свежий файл по дате изменения
        files = []
        for file in os.listdir(update_dir):
            if file.lower().startswith(self.type_version.lower()) and file.lower().endswith('.zip'):
                file_path = os.path.join(update_dir, file)
                files.append((file_path, os.path.getmtime(file_path)))

        if files:
            # Сортируем по дате изменения (новые сначала)
            files.sort(key=lambda x: x[1], reverse=True)
            return files[0][0]
        return None

    def extract_archive(self, archive_path):
        """Безопасная распаковка архива с обработкой кодировок"""
        try:
            # Очищаем папку перед распаковкой
            for item in os.listdir(self.extract_dir):
                item_path = os.path.join(self.extract_dir, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                else:
                    shutil.rmtree(item_path)

            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    # Безопасное извлечение имени файла
                    file_name = self._safe_decode_filename(file_info.filename)

                    # Защита от Zip Slip
                    target_path = os.path.join(self.extract_dir, file_name)
                    if not os.path.abspath(target_path).startswith(os.path.abspath(self.extract_dir)):
                        raise ValueError(f"Попытка распаковки вне целевой папки: {file_name}")

                    # Создаем папки если нужно
                    if file_name.endswith('/'):
                        os.makedirs(target_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, 'wb') as f:
                            f.write(zip_ref.read(file_info))
            return True

        except Exception as e:
            debug_logger.error(f"Ошибка распаковки: {str(e)}", exc_info=True)
            self.assistant.show_message(f"Ошибка распаковки: {str(e)}", "Ошибка", "error")
            return False

    def _safe_decode_filename(self, filename):
        """Безопасное декодирование имени файла из архива с поддержкой русского"""
        # Список кодировок для попытки декодирования (в порядке приоритета)
        encodings = [
            'cp866',  # DOS/Windows Russian
            'cp1251',  # Windows Cyrillic
            'utf-8',  # Unicode
            'cp437',  # DOS English
            'iso-8859-1',  # Latin-1
            'koi8-r'  # Russian KOI8-R
        ]

        # Сначала пробуем стандартное декодирование (для современных ZIP)
        try:
            return filename.encode('cp437').decode('utf-8')
        except UnicodeError:
            pass

        # Если не получилось, пробуем все кодировки по очереди
        for enc in encodings:
            try:
                return filename.encode('cp437').decode(enc)
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue

        # Если ничего не помогло, возвращаем как есть и логируем проблему
        debug_logger.warning(f"Не удалось декодировать имя файла: {filename}")
        return filename


class ChangelogWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(700, 600)

        # Основной контейнер с рамкой
        container = QWidget(self)
        container.setObjectName("WindowContainer")
        container.setGeometry(0, 0, self.width(), self.height())

        # Заголовок с крестиком
        title_bar = QWidget(container)
        title_bar.setObjectName("TitleBar")
        title_bar.setGeometry(1, 1, self.width() - 2, 35)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(5)

        title_label = QLabel("История изменений")
        title_label.setStyleSheet("background: transparent;")
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
        self.text_browser.setStyleSheet("background: transparent;")
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

    def _wait_and_save_screenshot(self, timeout=10):
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


def should_launch_updater():
    """Определяет нужно ли запускать updater"""
    # Не запускаем updater если:
    # 1. Это запуск после обновления (--updated)
    # 2. Updater уже запущен
    # 3. Это специальный режим (например, --no-update)
    if build_ini == "dev":
        return False

    if len(sys.argv) > 1 and sys.argv[1] == "--updated":
        return False

    # Проверяем, не запущен ли уже updater
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'Update.exe':
            return False

    return True


if __name__ == '__main__':
    try:
        # Запускаем updater если нужно
        if should_launch_updater():
            updater_path = get_path("Update.exe")
            if os.path.exists(updater_path):
                subprocess.Popen([updater_path])
                sys.exit(0)  # Закрываем основную программу

        # Продолжаем обычный запуск
        if len(sys.argv) > 1 and sys.argv[1] == "--updated":
            logger.info("Запуск после обновления")
        else:
            if activate_existing_window():
                sys.exit(0)

        app = QApplication([])
        app.setWindowIcon(QIcon(get_path('icon_assist.ico')))
        window = Assistant()
        app.exec_()

    except Exception as e:
        logger.error(f"Произошла ошибка при запуске программы: {e}")
        debug_logger.error(f"Произошла ошибка при запуске программы: {e}")

# if __name__ == '__main__':
#     try:
#         if activate_existing_window():
#             sys.exit(0)
#         app = QApplication([])
#         app.setWindowIcon(QIcon(get_path('icon_assist.ico')))
#         window = Assistant()
#
#         app.exec_()
#
#     except Exception as e:
#         logger.error(f"Произошла ошибка при запуске программы: {e}")
#         debug_logger.error(f"Произошла ошибка при запуске программы: {e}")
