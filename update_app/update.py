import json
import os
import shutil
import time
import psutil
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QGraphicsColorizeEffect, QSizePolicy
)
import sys
from pathlib import Path
import logging

logger = logging.getLogger("update")
logger.setLevel(logging.DEBUG)  # Уровень логирования

# Формат сообщений
formatter = logging.Formatter(
    fmt="[{levelname}] {asctime} | {message}",
    datefmt="%H:%M:%S",
    style="{"
)

# Обработчик: вывод в консоль
file_handler = logging.FileHandler("update.log", encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Добавляем обработчик к логгеру (если его ещё нет)
if not logger.handlers:
    logger.addHandler(file_handler)

def get_directory():
    """Автоматически определяет корневую директорию для всех режимов"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS  # onefile режим
        base = Path(sys.executable).parent
        internal = base / '_internal'
        return internal if internal.exists() else base
    return Path(__file__).parent  # режим разработки (корень проекта)

def get_path(*path_parts):
    """Строит абсолютный путь, идентичный в обоих режимах"""
    return str(get_directory() / Path(*path_parts))

def get_resource_path(relative_path):
    """Универсальный путь для ресурсов внутри/снаружи EXE"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            # Режим onefile: ресурсы во временной папке _MEIPASS
            base_path = Path(sys._MEIPASS)
        else:
            # Режим onedir: ресурсы в папке с EXE
            base_path = Path(sys.executable).parent
    else:
        # Режим разработки
        base_path = Path(__file__).parent

    return base_path / relative_path

def get_base_directory():
    """Возвращает правильный базовый путь в любом режиме"""
    if getattr(sys, 'frozen', False):
        # Режим exe (onefile или onedir)
        if hasattr(sys, '_MEIPASS'):
            # onefile режим - возвращаем папку с exe, а не временную
            return Path(sys.executable).parent
        # onedir режим
        return Path(sys.executable).parent
    # Режим разработки
    return Path(__file__).parent

class UpdateThread(QThread):
    status_update = pyqtSignal(str, int)
    update_complete = pyqtSignal(bool)

    def __init__(self, root_dir, base_dir, update_pack_dir):
        super().__init__()
        self.root_dir = root_dir
        self.base_dir = base_dir
        self.update_pack_dir = update_pack_dir

    def run(self):
        # Ждём закрытия основной программы
        self.status_update.emit("Ожидание завершения Assistant.exe...", 0)

        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'Assistant.exe':
                try:
                    proc.kill()  # Принудительно завершаем процесс
                except Exception as e:
                    logger.error(f"Ошибка завершения процесса: {e}")
                    self.update_complete.emit(False)
                    return

        # 🔥 2. Проверяем, что процесс закрыт (ждать не более 5 сек)
        for _ in range(5):
            if not any(p.info['name'] == 'Assistant.exe' for p in psutil.process_iter(['name'])):
                break
            time.sleep(1)
        else:
            self.status_update.emit("Ошибка: не удалось закрыть Assistant.exe!", 0)
            self.update_complete.emit(False)
            return

        self.status_update.emit("Удаление устаревших файлов...", 20)
        self.delete_old_files()

        self.status_update.emit("Копирование новых файлов...", 40)
        if self.copy_new_files():
            self.status_update.emit("Обновление завершено.", 100)
            self.update_complete.emit(True)
        else:
            self.status_update.emit("Ошибка копирования!", 0)
            self.update_complete.emit(False)

    def delete_old_files(self):
        preserved = ["user_settings", "update", "update_pack"]

        # Удаление внутри self.root_dir (как раньше)
        for item in os.listdir(self.root_dir):
            full_path = os.path.join(self.root_dir, item)
            if os.path.isdir(full_path):
                if os.path.basename(full_path) not in preserved:
                    shutil.rmtree(full_path, ignore_errors=True)
            elif os.path.isfile(full_path):
                if os.path.basename(full_path) != "Assistant.exe":
                    try:
                        os.remove(full_path)
                    except Exception as e:
                        logger.error(f"Ошибка при удалении старых файлов: {e}")
                        pass

        parent_dir = os.path.dirname(self.root_dir)  # Получаем родительскую папку
        assistant_exe_path = os.path.join(parent_dir, "Assistant.exe")

        if os.path.isfile(assistant_exe_path):
            try:
                os.remove(assistant_exe_path)
                logger.info(f"Удалён {assistant_exe_path}")
            except Exception as e:
                logger.error(f"Ошибка удаления {assistant_exe_path}: {e}")

    def copy_new_files(self):
        try:
            # Путь к папке _internal внутри update_pack
            update_internal_dir = os.path.join(self.update_pack_dir, "_internal")

            # Копируем содержимое _internal из update_pack в целевую _internal, кроме user_settings
            if os.path.exists(update_internal_dir):
                for item in os.listdir(update_internal_dir):
                    if item == "user_settings":
                        continue
                    if item == "Update.exe":
                        continue

                    src = os.path.join(update_internal_dir, item)
                    dst = os.path.join(self.root_dir, item)

                    # Пробуем 3 раза с задержкой
                    for _ in range(5):  # 5 попыток
                        try:
                            if os.path.isdir(src):
                                shutil.copytree(src, dst, dirs_exist_ok=True)
                            else:
                                # Сначала переименовываем старый файл
                                if os.path.exists(dst):
                                    try:
                                        os.rename(dst, dst + ".old")
                                    except:
                                        pass
                                shutil.copy2(src, dst)
                            break
                        except Exception:
                            time.sleep(1)

            # Копируем Assistant.exe на уровень выше
            assistant_src = os.path.join(self.update_pack_dir, "Assistant.exe")
            if os.path.exists(assistant_src):
                parent_dir = os.path.dirname(self.root_dir)  # Родительская папка
                assistant_dst = os.path.join(parent_dir, "Assistant.exe")
                shutil.copy2(assistant_src, assistant_dst)

            return True
        except Exception as e:
            logger.error(f"Ошибка копирования: {e}")
            return False


class UpdateWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.setWindowIcon(QIcon(get_path('icon.ico')))
        self.style_path = get_path('color.json')
        self.svg_path = get_path("owl_start.svg")
        self.style_manager = ApplyColor(self.style_path)
        self.styles = self.style_manager.load_styles()
        self.init_ui()
        self.apply_styles()
        self.start_update_process()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(250, 250)

        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.move(
            int((screen_geometry.width() - self.width()) / 2),
            int((screen_geometry.height() - self.height()) / 2)
        )
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        self.main_widget = QWidget()
        self.main_widget.setStyleSheet("""border-radius:20px""")
        content_layout = QVBoxLayout(self.main_widget)
        content_layout.setContentsMargins(15, 0, 15, 20)
        content_layout.addStretch()

        self.svg_image = QSvgWidget()
        self.svg_image.load(self.svg_path)
        self.svg_image.setFixedSize(130, 120)
        self.svg_image.setStyleSheet("""
                            background: transparent;
                            border: none;
                            outline: none;
                        """)
        self.color_svg = QGraphicsColorizeEffect()
        self.svg_image.setGraphicsEffect(self.color_svg)
        content_layout.addWidget(self.svg_image, alignment=Qt.AlignCenter)

        # Текст
        self.label = QLabel("Ожидание завершения программы...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        content_layout.addWidget(self.label)

        self.progress = QLabel("█" * 10)
        self.progress.setFixedWidth(200)
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setStyleSheet("font-family: monospace;")
        self.progress.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        content_layout.addWidget(self.progress)

        # Кнопка выхода
        self.error_button = QPushButton("Закрыть")
        self.error_button.clicked.connect(self.quit_application)
        self.error_button.setStyleSheet("""width:100px; border-radius:5px""")
        self.error_button.hide()
        content_layout.addWidget(self.error_button, alignment=Qt.AlignCenter)

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

            self.setStyleSheet(style_sheet)

        except Exception as e:
            logger.error(f"Ошибка в методе apply_styles: {e}")

    def start_update_process(self):
        if self.thread is not None:
            return  # Защита от повторного запуска
        self.label.setText("Проверка...")

        root_dir = get_base_directory()  # Корень (Assistant/)
        update_pack_dir = root_dir / "update_pack"

        # --- Проверяем наличие и содержимое update_pack ---
        if not os.path.exists(update_pack_dir):
            self.label.setText("Папка update_pack не найдена")
            self.show_error("Папка update_pack не найдена")
            return

        if self.is_folder_empty(update_pack_dir):
            self.label.setText("Папка update_pack пуста")
            self.show_error("Папка update_pack пуста")
            return

        self.label.setText("Обновление запущено...")
        self.thread = UpdateThread(
            root_dir=root_dir,
            base_dir=os.path.dirname(root_dir),
            update_pack_dir=update_pack_dir
        )
        self.thread.status_update.connect(self.set_status)
        self.thread.update_complete.connect(self.on_update_complete)
        self.thread.start()

    def is_folder_empty(self, folder):
        """Проверка с фильтрацией скрытых файлов"""
        visible_files = [f for f in os.listdir(folder) if not f.startswith('.')]
        return len(visible_files) == 0

    def on_update_complete(self, success):
        if success:
            QTimer.singleShot(1000, self.run_main_app)
        else:
            self.show_error("Не удалось обновить программу.")

    def run_main_app(self):
        main_app = os.path.join(os.path.dirname(get_base_directory()), "Assistant.exe")
        if os.path.exists(main_app):
            os.startfile(main_app)
        self.close()

    def set_status(self, text, progress=None):
        self.label.setText(text)
        if progress is not None:
            self.progress.setText("█" * int(progress / 5))

    def show_error(self, message):
        self.label.setText(message)
        self.error_button.show()

    def quit_application(self):
        sys.exit(1)

#     def start_update_process(self):
#         if self.thread is not None:
#             return  # Защита от повторного запуска
#
#         self.label.setText("Запуск имитации обновления...")
#
#         # === ВРЕМЕННАЯ ЗАМЕНА: используем имитацию ===
#         self.thread = MockUpdateThread()
#         # ==========================================
#
#         self.thread.status_update.connect(self.set_status)
#         self.thread.update_complete.connect(self.on_update_complete)
#         self.thread.start()
#
# class MockUpdateThread(QThread):
#     status_update = pyqtSignal(str, int)  # сообщение, процент
#     update_complete = pyqtSignal(bool, str)
#
#     def __init__(self):
#         super().__init__()
#
#     def run(self):
#         steps = [
#             "Подготовка...",
#             "Анализ обновления...",
#             "Копирование файлов...",
#             "Обновление конфигураций...",
#             "Очистка временных файлов..."
#         ]
#
#         for i, step in enumerate(steps):
#             # Имитация работы
#             for progress in range(0, 101, 5):  # 0, 5, 10, ..., 100
#                 self.status_update.emit(f"{step} {progress}%", progress + i * 20 // len(steps))
#                 time.sleep(0.03)  # Задержка для плавности
#
#             # Небольшая пауза между шагами
#             time.sleep(0.2)
#
#         # Завершаем
#         self.update_complete.emit(True, "Обновление успешно завершено")

class ApplyColor():
    def __init__(self, new_color=None, parent=None):
        self.parent = parent  # Сохраняем ссылку на родительское окно
        self.color_path = get_path('user_settings', 'color_settings.json')
        self.default_color_path = get_path('color_presets', 'default.json')
        self.styles = {}
        if new_color:
            self.color_path = new_color

    def load_styles(self):
        """Только загрузка стилей без применения"""
        try:
            with open(self.color_path, 'r') as file:
                self.styles = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            try:
                with open(self.default_color_path, 'r') as default_file:
                    self.styles = json.load(default_file)
            except (FileNotFoundError, json.JSONDecodeError):
                self.styles = {}
        return self.styles

    def apply_to_widget(self, widget, widget_name):
        """Применяет стиль к конкретному виджету"""
        if widget_name in self.styles:
            widget.setStyleSheet(self.format_style(self.styles[widget_name]))

    def apply_color_svg(self, svg_widget: QSvgWidget, strength: float) -> None:
        """Применяет цвет к SVG виджету"""
        if "TitleBar" in self.styles and "border-bottom" in self.styles["TitleBar"]:
            border_parts = self.styles["TitleBar"]["border-bottom"].split()
            for part in border_parts:
                if part.startswith('#'):
                    color_effect = QGraphicsColorizeEffect()
                    color_effect.setColor(QColor(part))
                    svg_widget.setGraphicsEffect(color_effect)
                    color_effect.setStrength(strength)
                    break

    def format_style(self, style_dict):
        """Форматирует стиль в строку"""
        return '; '.join(f"{key}: {value}" for key, value in style_dict.items())

    def get_color_from_border(self, widget_key):
        """Извлекает цвет из CSS-свойства border"""
        try:
            if widget_key and widget_key in self.styles:
                style = self.styles[widget_key]
                border_value = style.get("border", "")

                # Ищем цвет в форматах: #RRGGBB, rgb(), rgba()
                import re
                color_match = re.search(
                    r'#(?:[0-9a-fA-F]{3}){1,2}|rgb\([^)]*\)|rgba\([^)]*\)',
                    border_value
                )
                return color_match.group(0) if color_match else "#05B8CC"  # Цвет по умолчанию
        except Exception as e:
            logger.error(f"Ошибка извлечения цвета: {e}")
        return "#05B8CC"  # Возвращаем синий по умолчанию при ошибках

    def apply_progressbar(self, key=None, widget=None, style="solid"):
        """
        Применяет стиль к прогресс-бару
        :param style: стиль заполнения полоски
        :param key: Ключ из стилей для извлечения цвета (например "QPushButton")
        :param widget: Ссылка на виджет QProgressBar
        """
        if not widget or not hasattr(widget, 'setStyleSheet'):
            logger.warning("Не передан виджет или он не поддерживает стилизацию")
            return

        try:
            # Получаем цвет из стилей или используем по умолчанию
            color = self.get_color_from_border(key) if key else "#05B8CC"

            if style == "solid":
                progress_style = f"""
                    QProgressBar {{
                        border: 1px solid {self.adjust_color(color, brightness=-30)};
                        height: 20px;
                        text-align: center;
                    }}
                    QProgressBar::chunk {{
                        background: qlineargradient(
                            x1:0, y1:0, x2:1, y2:0,
                            stop:0 {self.adjust_color(color, brightness=-10)},
                            stop:1 {color}
                        );
                    }}
                """
            else:
                # Формируем стиль с плавной анимацией
                progress_style = f"""
                    QProgressBar {{
                        border: 1px solid {self.adjust_color(color, brightness=-30)};
                        border-radius: 5px;
                        background: {self.adjust_color(color, brightness=-80)};
                        height: 20px;
                        text-align: center;
                    }}
                    QProgressBar::chunk {{
                        background: qlineargradient(
                            x1:0, y1:0, x2:1, y2:0,
                            stop:0 {self.adjust_color(color, brightness=-10)},
                            stop:1 {color}
                        );
                        border-radius: 2px;
                        width: 20px;
                        margin: 1px;
                    }}
                """
            widget.setStyleSheet(progress_style)

        except Exception as e:
            logger.error(f"Ошибка применения стиля прогресс-бара: {e}")
            # Применяем минимальный рабочий стиль при ошибках
            widget.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                }
                QProgressBar::chunk {
                    background-color: #05B8CC;
                }
            """)

    def adjust_color(self, color, brightness=0):
        """
        Корректирует яркость цвета
        :param color: Исходный цвет (hex/rgb/rgba)
        :param brightness: Значение от -100 до 100
        :return: Новый цвет в hex-формате
        """
        from PyQt5.QtGui import QColor
        try:
            qcolor = QColor(color)
            if brightness > 0:
                return qcolor.lighter(100 + brightness).name()
            elif brightness < 0:
                return qcolor.darker(100 - brightness).name()
            return qcolor.name()
        except:
            return color

def main():
    app = QApplication(sys.argv)
    window = UpdateWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()