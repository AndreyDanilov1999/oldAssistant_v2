import json

from PyQt5.QtGui import QColor
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QGraphicsColorizeEffect

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

# class ApplyColor():
#     def __init__(self):
#         self.color_path = get_path('user_settings', 'color_settings.json')
#         self.default_color_path = get_path('bin', 'color_presets', 'default.json')
#         self.title_bar_widget = None
#         self.setStyleSheet = None
#         self.styles = {}
#
#     def load_and_apply_styles(self):
#         """
#         Загружает стили из файла и применяет их к элементам интерфейса.
#         Если файл не найден или поврежден, устанавливает значения по умолчанию.
#         """
#         try:
#             with open(self.color_path, 'r') as file:
#                 self.styles = json.load(file)
#         except (FileNotFoundError, json.JSONDecodeError):
#             try:
#                 with open(self.default_color_path, 'r') as default_file:
#                     self.styles = json.load(default_file)
#             except (FileNotFoundError, json.JSONDecodeError):
#                 self.styles = {}
#
#         # Применяем загруженные или значения по умолчанию
#         self.apply_styles()
#
#     def apply_styles(self):
#         # Устанавливаем objectName для виджетов
#         if hasattr(self, 'central_widget'):
#             self.central_widget.setObjectName("CentralWidget")
#         if hasattr(self, 'title_bar_widget'):
#             self.title_bar_widget.setObjectName("TitleBar")
#         if hasattr(self, 'container'):
#             self.title_bar_widget.setObjectName("ConfirmDialogContainer")
#         # Применяем стили к текущему окну
#         style_sheet = ""
#         for widget, styles in self.styles.items():
#             if widget.startswith("Q"):  # Для стандартных виджетов (например, QMainWindow, QPushButton)
#                 selector = widget
#             else:  # Для виджетов с objectName (например, TitleBar, CentralWidget)
#                 selector = f"#{widget}"
#
#             style_sheet += f"{selector} {{\n"
#             for prop, value in styles.items():
#                 style_sheet += f"    {prop}: {value};\n"
#             style_sheet += "}\n"
#
#         # Устанавливаем стиль для текущего окна
#         self.setStyleSheet(style_sheet)
#
#         # Применяем стили для label_version и label_message
#         if hasattr(self, 'label_version') and hasattr(self, 'styles') and 'label_version' in self.styles:
#             self.label_version.setStyleSheet(self.format_style(self.styles['label_version']))
#
#         if hasattr(self, 'label_message') and hasattr(self, 'styles') and 'label_message' in self.styles:
#             self.label_message.setStyleSheet(self.format_style(self.styles['label_message']))
#
#         if hasattr(self, 'update_label') and hasattr(self, 'styles') and 'update_label' in self.styles:
#             self.update_label.setStyleSheet(self.format_style(self.styles['update_label']))
#
#     def format_style(self, style_dict):
#         """Форматируем словарь стиля в строку для setStyleSheet"""
#         return '; '.join(f"{key}: {value}" for key, value in style_dict.items())
#
#     def apply_color_svg(self, svg_widget: QSvgWidget, strength: float) -> None:
#         """Читает цвет из JSON-файла стилей"""
#
#         with open(self.color_path) as f:
#             styles = json.load(f)
#
#         if "TitleBar" in styles and "border-bottom" in styles["TitleBar"]:
#             border_parts = styles["TitleBar"]["border-bottom"].split()
#             for part in border_parts:
#                 if part.startswith('#'):
#                     color_effect = QGraphicsColorizeEffect()
#                     color_effect.setColor(QColor(part))
#                     svg_widget.setGraphicsEffect(color_effect)
#                     color_effect.setStrength(strength)
#                     break