import ctypes
import os
import re
import pyaudio
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QWidget, QProgressBar, QApplication, QMessageBox, QPushButton, \
    QGraphicsColorizeEffect, QDialog, QSizePolicy
from bin.apply_color_methods import ApplyColor
from bin.toast_notification import SimpleNotice
from logging_config import debug_logger
from path_builder import get_path


class InitScreen(QWidget):
    """
    Окно инициализации программы, проверка файлов и необходимых параметров перед основным запуском
    """
    init_complete = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.style_manager = ApplyColor(self)
        self.color_path = self.style_manager.color_path
        self.styles = self.style_manager.load_styles()
        self.default_preset_style = get_path("bin", "color_presets", "default.json")
        self.style_path = get_path('user_settings', 'color_settings.json')
        self.svg_path = get_path("bin", "owl_start.svg")
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(250, 250)

        screen_geometry = self.screen().availableGeometry()
        self.move(
            (screen_geometry.width() - self.width()) // 2,
            (screen_geometry.height() - self.height()) // 2
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.main_widget = QWidget()
        content_layout = QVBoxLayout(self.main_widget)
        content_layout.setContentsMargins(15, 0, 15, 20)
        content_layout.addStretch()

        self.svg_image = QSvgWidget()
        self.svg_image.load(self.svg_path)
        self.svg_image.setFixedSize(140, 130)
        self.svg_image.setStyleSheet("""
                    background: transparent;
                    border: none;
                    outline: none;
                """)
        self.color_svg = QGraphicsColorizeEffect()
        self.svg_image.setGraphicsEffect(self.color_svg)
        content_layout.addWidget(self.svg_image, alignment=Qt.AlignCenter)

        content_layout.addStretch()

        self.label = QLabel("Инициализация...", self)
        self.label.setStyleSheet("background: transparent; min-height: 35px; max-height: 35px;")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        content_layout.addWidget(self.label)

        self.progress = QProgressBar(self)
        content_layout.addWidget(self.progress)

        # Кнопка выхода при ошибке
        self.error_button = QPushButton("Закрыть программу", self)
        self.error_button.clicked.connect(self.quit_application)
        self.error_button.hide()
        content_layout.addWidget(self.error_button)

        self.setLayout(layout)
        layout.addWidget(self.main_widget, 1)

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
            self.main_widget.setStyleSheet("""border:none; border-radius:20px""")
        except Exception as e:
            debug_logger.error(f"Ошибка в методе apply_styles: {e}")

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
            self.label.setText(f"Произошла ошибка")
            self.progress.setValue(0)
            self.show_message(text=f"{error}", title="Ошибка", message_type="error")
            self.init_complete.emit(False)  # Отправляем сигнал об ошибке
            QTimer.singleShot(1000, lambda: self.close())

    def finalize_initialization(self, success):
        self.init_complete.emit(success)
        self.close()


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
                QThread.msleep(5)  # имитация долгой проверки
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
            "lists.py", "other_options_window.py", "apply_color_methods.py", "check_update.py",
            "choose_color_window.py", "download_thread.py", "signals.py",
            "toast_notification.py", "widget_window.py")

        total_files = len(files_to_check)
        step_per_file = files_weight / total_files if total_files else 0

        for i, file in enumerate(files_to_check):
            path = get_path("bin", file)
            if not os.path.exists(path):
                self.progress_update.emit(f"Файл {file} не найден!", 0)
                self.checks_complete.emit(False, "", f"Файл {file} не найден!")  # Добавляем имя файла в сигнал
                return False

            progress = int((i + 1) * step_per_file) + 20
            self.progress_update.emit(f"Проверка {file}...", progress)
            QThread.msleep(10)  # Имитация работы

        return True

    def check_main_path(self, path, path_weight):
        self.progress_update.emit("Проверяю путь до исполняемого файла...", 21)
        for i in range(path_weight):
            QThread.msleep(5)  # имитация долгой проверки
            self.progress_update.emit("Проверяю путь до исполняемого файла...", 29)
        cyrillic_pattern = re.compile(r'[а-яА-ЯёЁ]')
        return bool(cyrillic_pattern.search(path))

    def input_device(self, device_weight):
        p = pyaudio.PyAudio()

        self.progress_update.emit("Ищу устройства ввода-вывода...", 10)
        for i in range(device_weight):
            QThread.msleep(5)  # имитация долгой проверки
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
            QThread.msleep(5)  # имитация долгой проверки
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
