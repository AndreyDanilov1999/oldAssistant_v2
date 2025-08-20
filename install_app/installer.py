import json
import re
import shutil
import subprocess
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QGraphicsColorizeEffect, QSizePolicy, QProgressBar, QSpacerItem, QFileDialog
)
import sys
from utils import get_path, logger, get_base_directory


class InstallerWindow(QWidget):
    """
    Инсталлятор
    """

    def __init__(self):
        super().__init__()
        self.root_dir = get_base_directory()
        self.update_pack_dir = self.root_dir / "update_pack"
        self.update_file_path = get_path("Update.exe")
        self.install_path = None
        self.setWindowIcon(QIcon(get_path('icon.ico')))
        self.parent_style = self.root_dir / "user_settings" / "color_settings.json"
        self.style_path = get_path('color.json')
        if self.parent_style.exists():
            style = self.parent_style
        else:
            style = self.style_path
        self.svg_path = get_path("logo.svg")
        self.style_manager = ApplyColor(style)
        self.styles = self.style_manager.load_styles()
        self.init_ui()
        self.apply_styles()
        self.start_installation_process()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
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
        content_layout.setContentsMargins(15, 0, 15, 10)
        content_layout.addStretch()

        self.svg_image = QSvgWidget()
        self.svg_image.load(self.svg_path)
        self.svg_image.setFixedSize(120, 110)
        self.svg_image.setStyleSheet("""
                            background: transparent;
                            border: none;
                            outline: none;
                        """)
        self.color_svg = QGraphicsColorizeEffect()
        self.svg_image.setGraphicsEffect(self.color_svg)
        content_layout.addWidget(self.svg_image, alignment=Qt.AlignCenter)

        # Текст
        self.label = QLabel("Выбор папки установки...")
        self.label.setStyleSheet("background-color: transparent;")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        content_layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(200)
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        content_layout.addWidget(self.progress)

        self.button_spacer = QSpacerItem(20, 0, QSizePolicy.Minimum, QSizePolicy.Fixed)
        content_layout.addItem(self.button_spacer)

        # Кнопка выбора папки
        self.folder_button = QPushButton("Выбрать папку")
        self.folder_button.clicked.connect(self.choice_folder_path)
        self.folder_button.setStyleSheet("""width:100px; border-radius:5px""")
        content_layout.addWidget(self.folder_button, alignment=Qt.AlignCenter)

        # Кнопка выхода
        self.error_button = QPushButton("Закрыть")
        self.error_button.clicked.connect(self.quit_application)
        self.error_button.setStyleSheet("""width:100px; border-radius:5px""")
        self.error_button.hide()
        content_layout.addWidget(self.error_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        layout.addWidget(self.main_widget, 1)

    def start_installation_process(self):
        """Начало процесса установки"""
        self.set_status("Выберите папку для установки", 0)

    def installer(self):
        try:
            if self.install_path:
                # создание структуры, копирование и запуск файла update.exe
                self.create_installation_structure(self.install_path)
            else:
                self.show_error("Папка не выбрана")
        except Exception as e:
            logger.error(f"Ошибка установки: {e}")
            self.show_error("Ошибка установки")

    def choice_folder_path(self):
        """Выбор папки для установки с проверкой на кириллицу"""
        try:
            folder = QFileDialog.getExistingDirectory(
                self,
                "Выберите папку для установки Assistant",
                str(Path.home()),
                QFileDialog.ShowDirsOnly
            )

            if folder:
                # Проверяем путь на наличие кириллицы
                if self.has_cyrillic(folder):
                    self.set_status("Ошибка: путь содержит кириллицу!", 0)
                    # Показываем кнопку снова для повторного выбора
                    self.folder_button.show()
                    return

                self.install_path = Path(folder)
                self.set_status("Подготовка компонентов...", 30)
                self.button_spacer.changeSize(20, 40)
                self.folder_button.hide()
                QTimer.singleShot(1000, self.installer)
            else:
                self.set_status("Папка не выбрана", 0)

        except Exception as e:
            logger.error(f"Ошибка выбора папки: {e}")
            self.show_error("Ошибка выбора папки")

    def has_cyrillic(self, text):
        """Проверяет, содержит ли текст кириллические символы с помощью regex"""
        return bool(re.search('[а-яА-ЯёЁ]', text))

    def create_installation_structure(self, install_path):
        """Создание структуры папок для установки"""
        try:
            self.set_status("Создание структуры установки...", 50)

            install_path = Path(install_path)
            # Создаем путь:
            assistant_dir = install_path / "Assistant"
            assistant_dir.mkdir(parents=True, exist_ok=True)

            # Создаем папку _internal внутри Assistant
            internal_dir = assistant_dir / "_internal"
            internal_dir.mkdir(parents=True, exist_ok=True)

            # Копируем сам Update.exe в папку _internal
            target_exe_path = internal_dir / "Update.exe"
            current_exe_path = self.update_file_path

            if current_exe_path != target_exe_path:
                shutil.copy2(current_exe_path, target_exe_path)

            logger.info(f"Структура создана: {assistant_dir}")

            self.set_status("Запуск обновления...", 100)
            QTimer.singleShot(1000, self.run_update)
        except Exception as e:
            logger.error(f"Ошибка создания структуры: {e}")
            self.show_error("Ошибка установки")

    def run_update(self):
        try:
            if self.install_path:
                internal_dir = self.install_path / "Assistant" / "_internal"
                update_exe_path = internal_dir / "Update.exe"

                if update_exe_path.exists():
                    subprocess.Popen([str(update_exe_path), "--install-mode"])
                    logger.info("Update.exe запущен")
                    self.close()
                else:
                    logger.info("Update.exe не найден")
                    self.show_error("Update.exe не найден")
        except Exception as e:
            logger.error(f"Ошибка при запуске Update.exe: {e}")
            self.show_error("Ошибка запуска")

    def set_status(self, text, progress=None):
        self.label.setText(text)
        if progress is not None:
            self.progress.setValue(progress)

    def show_error(self, message):
        self.label.setText(message)
        self.error_button.show()

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

    def quit_application(self):
        sys.exit(1)


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
        if "TitleBar" in self.styles and "border-bottom" in self.styles["TitleBar"]:
            border_value = self.styles["TitleBar"]["border-bottom"]
            color = QColor("#000000")  # Fallback

            # Ищем градиент в любой части строки
            gradient_match = re.search(r"qlineargradient\([^)]+\)", border_value)
            if gradient_match:
                gradient_str = gradient_match.group(0)
                # Ищем первый цвет градиента
                color_match = re.search(r"stop:0\s+(#[0-9a-fA-F]+)", gradient_str)
                if color_match:
                    color = QColor(color_match.group(1))
            else:
                # Стандартная обработка HEX-цвета
                hex_match = re.search(r"#[0-9a-fA-F]{3,6}", border_value)
                if hex_match:
                    color = QColor(hex_match.group(0))

            color_effect = QGraphicsColorizeEffect()
            color_effect.setColor(color)
            svg_widget.setGraphicsEffect(color_effect)
            color_effect.setStrength(strength)

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
                        border-radius: 5px;
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
    try:
        app = QApplication(sys.argv)
        window = InstallerWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"Ошибка {e}")

if __name__ == "__main__":
    main()