import json
import re

from PyQt5.QtGui import QColor
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QGraphicsColorizeEffect

from logging_config import debug_logger
from path_builder import get_path


class ApplyColor():
    def __init__(self, parent=None):
        self.parent = parent  # Сохраняем ссылку на родительское окно
        self.color_path = get_path('user_settings', 'color_settings.json')
        self.default_color_path = get_path('color_presets', 'default.json')
        self.styles = {}

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
            debug_logger.error(f"Ошибка извлечения цвета: {e}")
        return "#05B8CC"  # Возвращаем синий по умолчанию при ошибках

    def apply_progressbar(self, key=None, widget=None, style="solid"):
        """
        Применяет стиль к прогресс-бару
        :param style: стиль заполнения полоски
        :param key: Ключ из стилей для извлечения цвета (например "QPushButton")
        :param widget: Ссылка на виджет QProgressBar
        """
        if not widget or not hasattr(widget, 'setStyleSheet'):
            debug_logger.warning("Не передан виджет или он не поддерживает стилизацию")
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
            debug_logger.error(f"Ошибка применения стиля прогресс-бара: {e}")
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