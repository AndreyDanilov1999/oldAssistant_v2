import ctypes
import json
import os
import re

import pyaudio
import winsound
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QWidget, QProgressBar, QApplication, QMessageBox, QPushButton, \
    QGraphicsColorizeEffect, QHBoxLayout, QStyle, QDialog

from bin.apply_color_methods import ApplyColor
from logging_config import debug_logger
from path_builder import get_path


class InitScreen(QWidget):
    """
    Окно инициализации программы, проверка файлов и необходимых параметров перед основным запуском
    """
    init_complete = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.styles = None
        self.style_manager = ApplyColor(self)
        self.color_path = self.style_manager.color_path
        self.styles = self.style_manager.load_styles()
        self.default_preset_style = get_path("bin", "color_presets", "default.json")
        self.style_path = get_path('user_settings', 'color_settings.json')
        self.svg_path = get_path("bin", "owl_start.svg")
        self.init()
        self.apply_styles()

    def init(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(300, 300)
        screen_geometry = self.screen().availableGeometry()
        self.move(
            (screen_geometry.width() - self.width()) // 2,
            (screen_geometry.height() - self.height()) // 2
        )
        layout = QVBoxLayout()
        layout.addStretch()
        self.svg_image = QSvgWidget()
        self.svg_image.load(self.svg_path)
        self.svg_image.setFixedSize(180, 150)
        self.svg_image.setStyleSheet("""
                    background: transparent;
                    border: none;
                    outline: none;
                """)
        self.color_svg = QGraphicsColorizeEffect()
        self.svg_image.setGraphicsEffect(self.color_svg)
        layout.addWidget(self.svg_image, alignment=Qt.AlignCenter)

        layout.addStretch()

        self.label = QLabel("Инициализация...", self)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.progress = QProgressBar(self)
        layout.addWidget(self.progress)

        # Кнопка выхода при ошибке
        self.error_button = QPushButton("Закрыть программу", self)
        self.error_button.clicked.connect(self.quit_application)
        self.error_button.hide()
        layout.addWidget(self.error_button)

        self.setLayout(layout)

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
        dialog.setFixedSize(250, 180)

        # Основной контейнер с рамкой 1px
        container = QWidget(dialog)
        container.setObjectName("MessageContainer")
        container.setGeometry(0, 0, dialog.width(), dialog.height())

        title_bar = QWidget(container)
        title_bar.setObjectName("TitleBar")
        title_bar.setGeometry(1, 1, dialog.width() - 2, 35)

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

        icon_layout = QVBoxLayout(icon_widget)
        icon_layout.addWidget(icon_label)
        content_layout.addWidget(icon_widget)

        # Текст
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
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

    def quit_application(self):
        """Перенаправляем запрос на закрытие в главное окно"""
        self.main_window.cleanup_before_exit()

    def start_checks(self, main_window):
        self.main_window = main_window
        self.check_thread = CheckThread()
        self.check_thread.progress_update.connect(self.update_progress)
        self.check_thread.checks_complete.connect(self.on_checks_complete)
        self.check_thread.start()

    def update_progress(self, message, value):
        self.label.setText(message)
        self.progress.setValue(value)
        QApplication.processEvents()  # Обновляем интерфейс

    def on_checks_complete(self, result, missing_file="", error=""):
        if result:
            self.progress.setValue(100)
            QTimer.singleShot(1000, lambda: self.finalize_initialization(True))
        else:
            self.label.setText(f"Ошибка!")
            self.progress.setValue(0)
            if missing_file:
                QMessageBox.critical(self, "Ошибка",
                                     f"Не удалось найти {missing_file}")
            else:
                self.show_message(f"{error}", "Ошибка", "error")
            self.init_complete.emit(False)  # Отправляем сигнал об ошибке
            self.close()

    def finalize_initialization(self, success):
        self.init_complete.emit(success)
        self.close()

    def apply_styles(self):
        try:
            self.styles = self.style_manager.load_styles()

            # Применение к SVG
            self.style_manager.apply_color_svg(self.svg_image, strength=0.95)
            self.style_manager.apply_progressbar(key="QPushButton", widget=self.progress)

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
        except Exception as e:
            debug_logger.error(f"Ошибка в методе apply_styles: {e}")


class CheckThread(QThread):
    checks_complete = pyqtSignal(bool, str, str)
    progress_update = pyqtSignal(str, int)

    def run(self):
        try:
            total_steps = 100
            admin_weight = 10
            device_weight = 10
            path_weight = 10
            files_weight = 70

            self.progress_update.emit("Проверка прав администратора...", 0)
            if not self.check_admin():
                self.progress_update.emit("Ошибка: Нет прав администратора!", 0)
                self.checks_complete.emit(False, "", "Ошибка: Нет прав администратора!")
                return
            for i in range(admin_weight):
                QThread.msleep(10)  # имитация долгой проверки
                self.progress_update.emit("Проверка прав администратора...", i + 1)

            if not self.check_audio_devices(device_weight):
                return

            if self.check_main_path(get_path(), path_weight):
                self.checks_complete.emit(False, "", "Ошибка: В пути обнаружена кириллица!")
                return

            files_ok = self.check_main_files(files_weight)
            if not files_ok:
                return

            self.progress_update.emit("Запуск...", 100)
            self.checks_complete.emit(True, "", "")
        except Exception as e:
            self.progress_update.emit(f"Критическая ошибка: {str(e)}", 0)
            self.checks_complete.emit(False, "", "")

    def check_admin(self):
        """Проверка прав администратора"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def check_main_files(self, files_weight):
        files_to_check = (
            "settings_window.py", "speak_functions.py", "audio_control.py",
            "commands_settings_window.py", "func_list.py", "function_list_main.py",
            "guide_window.py", "lists.py", "other_options_window.py")

        total_files = len(files_to_check)
        step_per_file = files_weight / total_files if total_files else 0

        for i, file in enumerate(files_to_check):
            path = get_path("bin", file)
            if not os.path.exists(path):
                self.progress_update.emit(f"Файл {file} не найден!", 0)
                self.checks_complete.emit(False, file, "")  # Добавляем имя файла в сигнал
                return False

            progress = int((i + 1) * step_per_file) + 20
            self.progress_update.emit(f"Проверка {file}...", progress)
            QThread.msleep(100)  # Имитация работы

        return True

    def check_main_path(self, path, path_weight):
        self.progress_update.emit("Проверяю путь до исполняемого файла...", 21)
        for i in range(path_weight):
            QThread.msleep(10)  # имитация долгой проверки
            self.progress_update.emit("Проверяю путь до исполняемого файла...", 29)
        cyrillic_pattern = re.compile(r'[а-яА-ЯёЁ]')
        return bool(cyrillic_pattern.search(path))

    def input_device(self, device_weight):
        p = pyaudio.PyAudio()

        self.progress_update.emit("Ищу устройства ввода-вывода...", 10)
        for i in range(device_weight):
            QThread.msleep(10)  # имитация долгой проверки
            self.progress_update.emit("Ищу устройства ввода-вывода...", 14)

            try:
                default_input_device = p.get_default_input_device_info()
                return True
            except IOError:
                self.progress_update.emit("Ошибка: Нет устройств ввода звука.", 10)
                self.checks_complete.emit(False, "", "Ошибка: Нет устройств ввода звука")
                return False

    def output_device(self, device_weight):
        p = pyaudio.PyAudio()

        self.progress_update.emit("Ищу устройства ввода-вывода...", 15)
        for i in range(device_weight):
            QThread.msleep(10)  # имитация долгой проверки
            self.progress_update.emit("Ищу устройства ввода-вывода...", 19)
        try:
            default_output_device = p.get_default_output_device_info()
            return True
        except IOError:
            self.progress_update.emit("Ошибка: Нет устройств вывода звука.", 10)
            self.checks_complete.emit(False, "", "Ошибка: Нет устройств вывода звука")
            return False
        finally:
            p.terminate()

    def check_audio_devices(self, device_weight):
        if not self.input_device(device_weight) or not self.output_device(device_weight):
            return False

        self.progress_update.emit("Аудиоустройства проверены.", 20)
        return True
