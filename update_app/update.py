import json
import os
import shutil
import time

import psutil
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QGraphicsColorizeEffect
)

import sys
from pathlib import Path

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
                    print(f"Ошибка завершения процесса: {e}")
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
                    except Exception:
                        pass

        parent_dir = os.path.dirname(self.root_dir)  # Получаем родительскую папку
        assistant_exe_path = os.path.join(parent_dir, "Assistant.exe")

        if os.path.isfile(assistant_exe_path):
            try:
                os.remove(assistant_exe_path)
                print(f"Удалён {assistant_exe_path}")
            except Exception as e:
                print(f"Ошибка удаления {assistant_exe_path}: {e}")

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
            print(f"Ошибка копирования: {e}")
            return False


class UpdateWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.styles = None
        self.style_path = get_path('color.json')
        self.svg_path = get_path("owl_start.svg")
        self.init_ui()
        self.load_and_apply_styles()
        self.thread = None
        self.start_update_process()

    def init_ui(self):
        self.setWindowIcon(QIcon(get_path('icon.ico')))
        self.setFixedSize(300, 300)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.move(
            int((screen_geometry.width() - self.width()) / 2),
            int((screen_geometry.height() - self.height()) / 2)
        )
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

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

        # Текст
        self.label = QLabel("Ожидание завершения программы...")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # Прогрессбар
        self.progress = QLabel("█" * 20)

        layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        # Кнопка выхода
        self.error_button = QPushButton("Закрыть")
        self.error_button.clicked.connect(self.quit_application)
        self.error_button.hide()
        layout.addWidget(self.error_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def start_update_process(self):
        if self.thread is not None:
            return  # Защита от повторного запуска
        self.label.setText("Проверка...")

        root_dir = get_base_directory()  # Корень (Assistant/)
        update_pack_dir = root_dir / "update_pack"  # Исправленный путь к update_pack

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

    def load_and_apply_styles(self):
        """
        Загружает стили из файла и применяет их к элементам интерфейса.
        Если файл не найден или поврежден, устанавливает значения по умолчанию.
        """
        try:
            with open(self.style_path, 'r') as file:
                self.styles = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            try:
                with open(self.default_preset_style, 'r') as default_file:
                    self.styles = json.load(default_file)
            except (FileNotFoundError, json.JSONDecodeError):
                self.styles = {}

        # Применяем загруженные или значения по умолчанию
        self.apply_styles()
        self.apply_color_svg(self.style_path, self.svg_image)
        self.apply_progressbar()

    def get_color_from_border(self, widget_key):
        if widget_key in self.styles:
            style = self.styles[widget_key]
            border_value = style.get("border", "")
            import re
            match = re.search(r'#(?:[0-9a-fA-F]{3}){2}|rgb$.*?$|rgba$.*?$',
                              border_value)
            if match:
                return match.group(0)
        return "#cccccc"

    def apply_progressbar(self):
        color = self.get_color_from_border("QPushButton")

        progress_style = f"""
            QProgressBar {{
                border-radius: 5px;
                text-align:center
            }}
            QProgressBar::chunk {{
                background-color: {color}
            }}
        """

        self.progress.setStyleSheet(progress_style)

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

    def format_style(self, style_dict):
        """Форматируем словарь стиля в строку для setStyleSheet"""
        return '; '.join(f"{key}: {value}" for key, value in style_dict.items())

    def apply_color_svg(self, style_file: str, svg_widget: QSvgWidget, strength: float = 0.99) -> None:
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

def main():
    app = QApplication(sys.argv)
    window = UpdateWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()