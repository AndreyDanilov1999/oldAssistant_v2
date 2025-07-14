import json
import os
import sys
from PyQt5.QtGui import QColor
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, \
    QGraphicsColorizeEffect, QApplication, QDialog, QLabel
from PyQt5.QtCore import Qt, QPoint, QSize, QPropertyAnimation, QRect
from bin.function_list_main import shutdown_windows
from bin.signals import color_signal
from logging_config import debug_logger
from path_builder import get_path


class WindowStateManager:
    def __init__(self, config_path=get_path("user_settings", "widget_state.json")):
        self.config_path = config_path
        self.default_state = {
            "window_position": {"x": 100, "y": 100},
            "window_size": {"width": 220, "height": 300},
            "is_compact": False,
            "is_pinned": False
        }

        # Создаем файл при инициализации, если его нет
        if not os.path.exists(self.config_path):
            self.save_state(self.default_state)

    def load_state(self):
        """Загружает состояние окна из JSON файла"""
        try:
            with open(self.config_path, 'r') as f:
                state = json.load(f)
                # Объединяем с default_state для обратной совместимости
                return {**self.default_state, **state}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка загрузки состояния: {e}, используются значения по умолчанию")
            return self.default_state.copy()

    def save_state(self, state):
        """Сохраняет состояние окна в JSON файл"""
        try:
            # Создаем папку, если ее нет
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, 'w') as f:
                json.dump(state, f, indent=4)
        except IOError as e:
            print(f"Ошибка сохранения состояния: {e}")

    def save_window_state(self, window):
        """Специальный метод для сохранения состояния QWidget"""
        state = {
            "window_position": {
                "x": window.pos().x(),
                "y": window.pos().y()
            },
            "window_size": {
                "width": window.width(),
                "height": window.height()
            },
            "is_compact": getattr(window, 'is_compact', False),
            "is_pinned": getattr(window, 'is_pinned', False),
        }
        self.save_state(state)

    def apply_state(self, window):
        """Применяет сохраненное состояние к окну"""
        state = self.load_state()

        window.move(QPoint(state["window_position"]["x"],
                           state["window_position"]["y"]))
        window.resize(QSize(state["window_size"]["width"],
                            state["window_size"]["height"]))

        # Устанавливаем дополнительные состояния
        window.is_compact = state["is_compact"]
        window.is_pinned = state["is_pinned"]

        return state


class SmartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.buttons_data = {}
        color_signal.color_changed.connect(self.update_colors)
        self.camera_path = get_path("bin", "icons", "camera.svg")
        self.power_path = get_path("bin", "icons", "power.svg")
        self.open_main_path = get_path("bin", "icons", "open_main.svg")
        self.settings_path = get_path("bin", "icons", "settings.svg")
        self.shortcut_path = get_path("bin", "icons", "shortcut.svg")
        self.color_path = get_path("user_settings", "color_settings.json")
        self.pin_path = get_path("bin", "icons", "push_pin.svg")
        self.lock_path = get_path("bin", "icons", "lock.svg")
        self.close_path = get_path("bin", "icons", "cancel.svg")
        self.resize_path = get_path("bin", "icons", "resize.svg")
        # Менеджер состояния окна
        self.state_manager = WindowStateManager()
        self.load_and_apply_styles()

        saved_state = self.state_manager.apply_state(self)

        base_flags = Qt.FramelessWindowHint | Qt.Tool
        if self.is_compact:
            self.compact_ui()
        else:
            self.init_ui()

        if self.is_pinned:
            base_flags |= Qt.WindowStaysOnTopHint

        self.setWindowFlags(base_flags)
        # Для перемещения окна
        self.old_pos = None

    def init_ui(self):
        # Настройки окна
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget {
                background: rgba(30, 30, 30, 180);
                border-radius: 10px;
            }
        """)
        self.setFixedSize(220, 300)

        # Главный layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем контейнер для всего содержимого (включая заголовок)
        container = QWidget()
        container.setObjectName("MainContainer")
        container.setStyleSheet("""
            #MainContainer {
                background: rgba(30, 30, 30, 180);
                border-radius: 10px;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Панель заголовка (теперь часть основного окна)
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("""
            #TitleBar {
                background: transparent;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid rgba(70, 70, 70, 100);
            }
        """)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(2, 0, 2, 0)
        title_layout.setSpacing(2)

        # Добавляем кнопки в заголовок
        self.pin_btn = QPushButton()
        self.pin_btn.setFixedSize(20, 20)
        self.pin_btn.setToolTip("Поверх других окон")
        self.pin_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(40, 110, 230, 80%);
            }
        """)
        self.pin_btn.clicked.connect(self.pin_widget)

        self.pin_svg = QSvgWidget(self.pin_path, self.pin_btn)
        self.pin_svg.setFixedSize(13, 13)
        self.pin_svg.move(3, 3)
        self.pin_svg.setStyleSheet("background: transparent; border: none;")

        self.lock_btn = QPushButton()
        self.lock_btn.setFixedSize(20, 20)
        self.lock_btn.setToolTip("Запомнить положение виджета")
        self.lock_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(40, 110, 230, 80%);
            }
        """)
        self.lock_svg = QSvgWidget(self.lock_path, self.lock_btn)
        self.lock_svg.setFixedSize(13, 13)
        self.lock_svg.move(3, 3)
        self.lock_svg.setStyleSheet("background: transparent; border: none;")
        self.lock_btn.clicked.connect(self.save_state)

        self.resize_btn = QPushButton()
        self.resize_btn.setFixedSize(20, 20)
        self.resize_btn.setToolTip("Компактный режим")
        self.resize_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(40, 110, 230, 80%);
            }
        """)
        self.resize_btn.clicked.connect(self.resize_widget)
        self.resize_svg = QSvgWidget(self.resize_path, self.resize_btn)
        self.resize_svg.setFixedSize(13, 13)
        self.resize_svg.move(3, 3)
        self.resize_svg.setStyleSheet("background: transparent; border: none;")

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setToolTip("Закрыть")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(230, 37, 37, 80%);
            }
        """)
        self.close_btn.clicked.connect(self.close)
        self.close_svg = QSvgWidget(self.close_path, self.close_btn)
        self.close_svg.setFixedSize(13, 13)
        self.close_svg.move(3, 3)
        self.close_svg.setStyleSheet("background: transparent; border: none;")

        # Добавляем элементы в заголовок
        title_layout.addStretch()
        title_layout.addWidget(self.pin_btn)
        title_layout.addWidget(self.lock_btn)
        title_layout.addWidget(self.resize_btn)
        title_layout.addWidget(self.close_btn)

        # Основная область с кнопками
        content_widget = QWidget()
        content_widget.setObjectName("ContentWidget")
        content_widget.setStyleSheet("""
            #ContentWidget {
                background: transparent;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(5)

        # Кнопки с иконками
        buttons_widget = QWidget()
        buttons_widget.setStyleSheet("background: transparent;")
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(5)

        # Настройки кнопок
        buttons_config = {
            'power_btn': {
                'icon': self.power_path,
                'tooltip': 'Выключить Компьютер',
                'action': self.shutdown_system
            },
            'settings_btn': {
                'icon': self.settings_path,
                'tooltip': 'Открыть настройки',
                'action': self.open_settings
            },
            'scrn_folder_btn': {
                'icon': self.camera_path,
                'tooltip': 'Открыть папку скриншотов',
                'action': self.assistant.open_folder_screenshots
            },
            'link_btn': {
                'icon': self.shortcut_path,
                'tooltip': 'Открыть папку с ярлыками',
                'action': self.assistant.open_folder_shortcuts
            },
            'open_main_btn': {
                'icon': self.open_main_path,
                'tooltip': 'Развернуть основное окно',
                'action': self.open_main_window
            }
        }

        # Создаем кнопки
        for btn_name, config in buttons_config.items():
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setToolTip(config['tooltip'])
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background: rgba(60, 60, 60, 100);
                    border-radius: 5px;
                }
            """)

            svg = QSvgWidget(config['icon'], btn)
            svg.setFixedSize(30, 30)
            svg.move(5, 5)

            self.buttons_data[btn_name] = {'button': btn, 'svg': svg}
            self.apply_color_svg(self.color_path, svg)
            btn.clicked.connect(config['action'])

            setattr(self, btn_name, btn)
            buttons_layout.addWidget(btn)

        buttons_layout.addStretch()

        # Собираем все вместе
        content_layout.addWidget(buttons_widget)
        content_layout.addStretch()

        container_layout.addWidget(title_bar)
        container_layout.addWidget(content_widget)

        main_layout.addWidget(container)

        # Для перетаскивания окна
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent

    def compact_ui(self):
        # Настройки окна
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
                    QWidget {
                        background: rgba(30, 30, 30, 180);
                        border-radius: 10px;
                    }
                """)
        self.setFixedSize(80, 250)

        # Главный layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем контейнер для всего содержимого (включая заголовок)
        container = QWidget()
        container.setObjectName("MainContainer")
        container.setStyleSheet("""
                    #MainContainer {
                        background: rgba(30, 30, 30, 180);
                        border-radius: 10px;
                    }
                """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Панель заголовка (теперь часть основного окна)
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("""
                    #TitleBar {
                        background: transparent;
                        border-top-left-radius: 10px;
                        border-top-right-radius: 10px;
                        border-bottom: 1px solid rgba(70, 70, 70, 100);
                    }
                """)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(2, 0, 2, 0)
        title_layout.setSpacing(2)

        # Добавляем кнопки в заголовок
        self.pin_btn = QPushButton()
        self.pin_btn.setFixedSize(20, 20)
        self.pin_btn.setToolTip("Поверх других окон")
        self.pin_btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                    }
                    QPushButton:hover {
                        background: rgba(40, 110, 230, 80%);
                    }
                """)
        self.pin_btn.clicked.connect(self.pin_widget)

        self.pin_svg = QSvgWidget(self.pin_path, self.pin_btn)
        self.pin_svg.setFixedSize(13, 13)
        self.pin_svg.move(3, 3)
        self.pin_svg.setStyleSheet("background: transparent; border: none;")

        self.lock_btn = QPushButton()
        self.lock_btn.setFixedSize(20, 20)
        self.lock_btn.setToolTip("Запомнить положение виджета")
        self.lock_btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                    }
                    QPushButton:hover {
                        background: rgba(40, 110, 230, 80%);
                    }
                """)
        self.lock_svg = QSvgWidget(self.lock_path, self.lock_btn)
        self.lock_svg.setFixedSize(13, 13)
        self.lock_svg.move(3, 3)
        self.lock_svg.setStyleSheet("background: transparent; border: none;")
        self.lock_btn.clicked.connect(self.save_state)

        self.resize_btn = QPushButton()
        self.resize_btn.setFixedSize(20, 20)
        self.resize_btn.setToolTip("Компактный режим")
        self.resize_btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                    }
                    QPushButton:hover {
                        background: rgba(40, 110, 230, 80%);
                    }
                """)
        self.resize_btn.clicked.connect(self.resize_widget)
        self.resize_svg = QSvgWidget(self.resize_path, self.resize_btn)
        self.resize_svg.setFixedSize(13, 13)
        self.resize_svg.move(3, 3)
        self.resize_svg.setStyleSheet("background: transparent; border: none;")

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setToolTip("Закрыть")
        self.close_btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                    }
                    QPushButton:hover {
                        background: rgba(230, 37, 37, 80%);
                    }
                """)
        self.close_btn.clicked.connect(self.close)
        self.close_svg = QSvgWidget(self.close_path, self.close_btn)
        self.close_svg.setFixedSize(13, 13)
        self.close_svg.move(3, 3)
        self.close_svg.setStyleSheet("background: transparent; border: none;")

        # Добавляем элементы в заголовок
        title_layout.addWidget(self.pin_btn)
        title_layout.addWidget(self.lock_btn)
        title_layout.addWidget(self.resize_btn)
        title_layout.addWidget(self.close_btn)

        # Основная область с кнопками
        content_widget = QWidget()
        content_widget.setObjectName("ContentWidget")
        content_widget.setStyleSheet("""
                    #ContentWidget {
                        background: transparent;
                        border-bottom-left-radius: 10px;
                        border-bottom-right-radius: 10px;
                    }
                """)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(5)

        # Кнопки с иконками
        buttons_widget = QWidget()
        buttons_widget.setStyleSheet("background: transparent;")
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(5)

        # Настройки кнопок
        buttons_config = {
            'power_btn': {
                'icon': self.power_path,
                'tooltip': 'Выключить Компьютер',
                'action': self.shutdown_system
            },
            'settings_btn': {
                'icon': self.settings_path,
                'tooltip': 'Открыть настройки',
                'action': self.open_settings
            },
            'scrn_folder_btn': {
                'icon': self.camera_path,
                'tooltip': 'Открыть папку скриншотов',
                'action': self.assistant.open_folder_screenshots
            },
            'link_btn': {
                'icon': self.shortcut_path,
                'tooltip': 'Открыть папку с ярлыками',
                'action': self.assistant.open_folder_shortcuts
            },
            'open_main_btn': {
                'icon': self.open_main_path,
                'tooltip': 'Развернуть основное окно',
                'action': self.open_main_window
            }
        }

        # Создаем кнопки
        for btn_name, config in buttons_config.items():
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setToolTip(config['tooltip'])
            btn.setStyleSheet("""
                        QPushButton {
                            background: transparent;
                            border: none;
                        }
                        QPushButton:hover {
                            background: rgba(60, 60, 60, 100);
                            border-radius: 5px;
                        }
                    """)

            svg = QSvgWidget(config['icon'], btn)
            svg.setFixedSize(30, 30)
            svg.move(5, 5)

            self.buttons_data[btn_name] = {'button': btn, 'svg': svg}
            self.apply_color_svg(self.color_path, svg)
            btn.clicked.connect(config['action'])

            setattr(self, btn_name, btn)
            buttons_layout.addWidget(btn, alignment=Qt.AlignCenter)

        buttons_layout.addStretch()

        # Собираем все вместе
        content_layout.addWidget(buttons_widget)
        content_layout.addStretch()

        container_layout.addWidget(title_bar)
        container_layout.addWidget(content_widget)

        main_layout.addWidget(container)

        # Для перетаскивания окна
        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent

    # Методы для перемещения окна
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()

    def load_window_state(self):
        """Загружает состояние окна из JSON"""
        state = self.state_manager.load_state()
        pos = state["window_position"]
        size = state["window_size"]
        self.move(QPoint(pos["x"], pos["y"]))
        self.resize(QSize(size["width"], size["height"]))

    def pin_widget(self):
        try:
            self.is_pinned = not self.is_pinned

            # Получаем текущие флаги (без изменения)
            flags = self.windowFlags()

            # Обновляем флаг поверх окон
            if self.is_pinned:
                flags |= Qt.WindowStaysOnTopHint
            else:
                flags &= ~Qt.WindowStaysOnTopHint

            # Применяем флаги и обновляем окно
            self.setWindowFlags(flags)
            self.show()  # Обязательно после изменения флагов!

            self.state_manager.save_window_state(self)
        except Exception as e:
            print(f"Ошибка {e}")

    def resize_widget(self):
        # Сохраняем текущую геометрию
        old_geometry = self.geometry()

        # Переключаем состояние
        self.is_compact = not getattr(self, 'is_compact', False)

        # Сохраняем текущее состояние pinned перед очисткой UI
        current_pinned_state = getattr(self, 'is_pinned', False)

        # Определяем новые размеры
        if self.is_compact:
            new_width, new_height = 80, 250  # Compact размер
        else:
            new_width, new_height = 220, 300  # Normal размер

        # Вычисляем новую позицию (сохраняем правый край)
        new_x = old_geometry.right() - new_width
        new_y = old_geometry.top()

        # Полностью очищаем текущий UI
        self.clear_ui()

        # Создаем новый UI в зависимости от состояния
        if self.is_compact:
            self.compact_ui()
        else:
            self.init_ui()

        # Восстанавливаем состояние pinned
        self.is_pinned = current_pinned_state
        if self.is_pinned:
            flags = self.windowFlags() | Qt.WindowStaysOnTopHint
            self.setWindowFlags(flags)
            self.show()

        # Создаем анимацию
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(50)
        self.animation.setStartValue(old_geometry)
        self.animation.setEndValue(QRect(new_x, new_y, new_width, new_height))

        # Запускаем анимацию
        self.animation.start()

    def clear_ui(self):
        # Удаляем все дочерние виджеты
        for child in self.findChildren(QWidget):
            if child != self:  # Не удаляем сам главный виджет
                child.deleteLater()

        # Удаляем текущий layout
        if self.layout():
            QWidget().setLayout(self.layout())

    def shutdown_system(self):
        """Выключает компьютер после подтверждения"""
        try:
            # Создаем кастомное окно вместо QMessageBox
            confirm_dialog = QDialog(self)
            confirm_dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            confirm_dialog.setFixedSize(110, 80)

            # Основной контейнер
            main_layout = QVBoxLayout(confirm_dialog)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(5)

            # Текст (с автоматическим переносом слов)
            label = QLabel("Выключить комп?")  # Укороченный текст для маленького окна
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 12px;
                    padding: 0;
                }
            """)
            main_layout.addWidget(label)

            # Контейнер для кнопок
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(5)

            # Кнопки
            yes_btn = QPushButton("Да")
            no_btn = QPushButton("Нет")

            # Стилизация кнопок
            btn_style = """
                QPushButton {
                    background: rgba(70, 70, 70, 160);
                    color: white;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 3px;
                    width: 20px;
                    height: 20px;
                    font-size: 12px;
                }
            """
            yes_btn.setStyleSheet(btn_style)
            no_btn.setStyleSheet(btn_style)

            btn_layout.addStretch()
            btn_layout.addWidget(yes_btn)
            btn_layout.addWidget(no_btn)
            btn_layout.addStretch()

            main_layout.addWidget(btn_container)

            # Обработчики кнопок
            yes_btn.clicked.connect(lambda: confirm_dialog.accept())
            no_btn.clicked.connect(lambda: confirm_dialog.reject())

            # Показываем и ждем результат
            if confirm_dialog.exec_() == QDialog.Accepted:
                try:
                    shutdown_windows()
                except Exception as e:
                    debug_logger.error(f"Ошибка выключения: {e}")

        except Exception as e:
            debug_logger.error(f"Ошибка диалога: {e}")

    def open_settings(self):
        try:
            self.assistant.show()
            self.assistant.open_main_settings()
        except Exception as e:
            debug_logger.error(f"Ошибка при открытии окна настроек через виджет {e}")

    def open_main_window(self):
        try:
            self.assistant.show()
        except Exception as e:
            debug_logger.error(f"Ошибка при открытии основного окна через виджет {e}")

    def save_state(self):
        self.state_manager.save_window_state(self)

    def closeEvent(self, event):
        # Сохраняем состояние виджета
        self.save_state()

        # Проверяем состояние главного окна
        if self.assistant:
            if self.assistant.isVisible() and not self.assistant.isMinimized():
                # Если главное окно видимо и не свернуто - просто закрываем виджет
                pass
            else:
                # В противном случае вызываем специальный метод
                self.assistant.restore_and_hide()

        super().closeEvent(event)

    def load_and_apply_styles(self):
        """
        Загружает стили из файла и применяет их к элементам интерфейса.
        Если файл не найден или поврежден, устанавливает значения по умолчанию.
        """
        try:
            with open(self.color_path, 'r') as file:
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

    def update_colors(self):
        for name, data in self.buttons_data.items():
            self.apply_color_svg(self.color_path, data['svg'])

    def apply_color_svg(self, style_file: str, svg_widget: QSvgWidget, strength: float = 0.90) -> None:
        """Читает цвет из JSON-файла стилей и применяет к SVG виджету"""
        try:
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
        except Exception as e:
            debug_logger.error(f"Ошибка в методе apply_color_svg: {e}")

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     monitor = SmartWidget()
#     monitor.show()
#     sys.exit(app.exec_())