import winsound
from PyQt5 import sip
from PyQt5.QtCore import QParallelAnimationGroup, QEasingCurve, QPropertyAnimation, QPoint, QEvent, QTimer, \
    QAbstractAnimation, Qt
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QApplication, QLabel, QGraphicsColorizeEffect, QHBoxLayout, QWidget, QVBoxLayout, QDialog, \
    QMessageBox, QPushButton

from bin.apply_color_methods import ApplyColor
from logging_config import debug_logger
from path_builder import get_path


class ToastNotification(QDialog):
    """
    Окно всплывающего уведомления
    """
    _active_toast = None

    def __init__(self, parent=None, message="", timeout=3000):
        super().__init__(parent)
        if ToastNotification._active_toast:
            ToastNotification._active_toast.close_immediately()

            # Сохраняем ссылку на текущее уведомление
        ToastNotification._active_toast = self
        self.parent = parent
        if self.parent:
            self.parent.installEventFilter(self)
        self.timeout = timeout
        self.message = message
        self.svg_path = get_path("bin", "owl_start.svg")
        self.style_path = get_path('user_settings', 'color_settings.json')
        self.style_manager = ApplyColor(self)
        self.styles = self.style_manager.load_styles()
        self.init_ui()
        self.apply_styles()

        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)  # Продолжительность анимации прозрачности
        self.opacity_animation.setKeyValueAt(0.0, 0.0)
        self.opacity_animation.setKeyValueAt(0.7, 0.0)
        self.opacity_animation.setKeyValueAt(1.0, 1.0)

        # Модифицируем анимацию позиции для движения сверху вниз
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.animation.setDuration(700)

    def init_ui(self):
        # Настройки окна
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(300, 100)

        # Основной layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Заголовок (TitleBar) ---
        self.title_bar = QWidget()
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setFixedHeight(1)
        main_layout.addWidget(self.title_bar)

        # --- Контент: иконка + текст ---
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        # Иконка
        self.svg_image = QSvgWidget()
        self.svg_image.load(self.svg_path)
        self.svg_image.setFixedSize(50, 50)
        self.svg_image.setStyleSheet("background: transparent; border: none;")
        self.color_svg = QGraphicsColorizeEffect()
        self.svg_image.setGraphicsEffect(self.color_svg)
        content_layout.addWidget(self.svg_image, alignment=Qt.AlignCenter | Qt.AlignRight)

        # Текст
        self.label = QLabel(self.message)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignVCenter)
        content_layout.addWidget(self.label, stretch=1)

        main_layout.addWidget(content_widget)

        self.setLayout(main_layout)

        # --- Анимация и таймер ---
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.animation.setDuration(500)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_animated)

    def eventFilter(self, obj, event):
        """Обработка событий родительского окна"""
        if ToastNotification._active_toast:
            if obj == self.parent:
                if event.type() == QEvent.WindowStateChange:
                    if self.parent.isActiveWindow():
                        self.handle_parent_restored()
                elif event.type() == QEvent.Hide:
                    if self.parent.isHidden():
                        self.handle_parent_hidden()
        return super().eventFilter(obj, event)

    def handle_parent_minimized(self):
        """Родитель свернут в трей"""
        if hasattr(self, 'animation_group') and self.animation_group.state() == QAbstractAnimation.Running:
            self.animation_group.stop()

        self.close_immediately()

    def handle_parent_restored(self):
        """Родитель восстановлен из трея"""
        # Можно автоматически показать уведомление снова, если нужно
        pass

    def handle_parent_hidden(self):
        """Родитель скрыт (например, закрыт)"""
        self.close_immediately()

    def recalculate_position(self):
        """Пересчет позиции уведомления"""
        if self.parent and not self.parent.isMinimized():
            parent_geo = self.parent.geometry()
            end_x = parent_geo.right() - self.width()
            end_y = parent_geo.top() + 34
            self.move(end_x, end_y)
        else:
            screen_geo = QApplication.primaryScreen().geometry()
            end_x = screen_geo.width() - self.width()
            end_y = 0
            self.move(end_x, end_y)

    def close_immediately(self):
        """Безопасное закрытие уведомления без анимации"""
        try:
            # 1. Останавливаем все анимации и таймеры
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()

            if hasattr(self, 'animation') and self.animation.state() == QPropertyAnimation.Running:
                self.animation.stop()

            if hasattr(self, 'animation_group') and self.animation_group.state() == QParallelAnimationGroup.Running:
                self.animation_group.stop()

            if hasattr(self, 'opacity_animation') and self.opacity_animation.state() == QPropertyAnimation.Running:
                self.opacity_animation.stop()

            # 2. Проверяем, существует ли еще виджет
            if not sip.isdeleted(self):
                # 3. Скрываем вместо закрытия (более безопасно)
                self.hide()

                # 4. Отсоединяем от родителя, если он существует
                if self.parent and not sip.isdeleted(self.parent):
                    self.setParent(None)

                # 5. Планируем реальное удаление
                self.deleteLater()

            # 6. Очищаем ссылку
            if ToastNotification._active_toast is self:
                ToastNotification._active_toast = None

        except Exception as e:
            debug_logger.error(f"Ошибка при закрытии уведомления: {e}")

    def showEvent(self, event):
        # Устанавливаем начальную прозрачность
        self.setWindowOpacity(0.0)

        screen_geo = QApplication.primaryScreen().availableGeometry()

        if self.parent and self.parent.isVisible() and not self.parent.isMinimized():
            # Если есть видимый родитель - позиционируем относительно него
            parent_geo = self.parent.geometry()
            start_x = parent_geo.right() - self.width()
            start_y = parent_geo.top() - self.height()
            end_x = start_x
            end_y = parent_geo.top() + 90
        else:
            # Иначе - позиционируем в правом верхнем углу экрана
            start_x = screen_geo.width() - self.width()  # 10px отступ от края
            start_y = -self.height()
            end_x = start_x
            end_y = 21  # 10px отступ сверху

        self.move(start_x, start_y)
        self.show()

        # Настраиваем анимацию позиции
        self.animation.setStartValue(QPoint(start_x, start_y))
        self.animation.setEndValue(QPoint(end_x, end_y))

        # Запускаем обе анимации параллельно
        self.animation.start()
        self.opacity_animation.start()

        # Таймер для автоматического скрытия
        self.timer.start(self.timeout)

    def hide_animated(self):
        """Анимация скрытия с изменением прозрачности"""
        # Создаем анимацию для исчезновения
        hide_opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        hide_opacity_animation.setDuration(500)
        hide_opacity_animation.setKeyValueAt(0.0, 1.0)
        hide_opacity_animation.setKeyValueAt(0.1, 0.8)
        hide_opacity_animation.setKeyValueAt(0.4, 0.0)
        hide_opacity_animation.setKeyValueAt(1.0, 0.0)

        current_pos = self.pos()
        end_pos = QPoint(current_pos.x(), -self.height())

        # Настраиваем анимацию движения вверх
        move_animation = QPropertyAnimation(self, b"pos")
        move_animation.setDuration(500)
        move_animation.setStartValue(current_pos)
        move_animation.setEndValue(end_pos)
        move_animation.setEasingCurve(QEasingCurve.InQuad)

        # Группируем анимации
        self.animation_group = QParallelAnimationGroup()
        self.animation_group.addAnimation(hide_opacity_animation)
        self.animation_group.addAnimation(move_animation)
        self.animation_group.finished.connect(self.close_immediately)
        self.animation_group.start()

    def apply_styles(self):
        try:
            self.styles = self.style_manager.load_styles()
            # Применение к SVG
            self.style_manager.apply_color_svg(self.svg_image, strength=0.95)

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


class SimpleNotice():
    def __init__(self, parent=None, message="", title="Уведомление", message_type="info", buttons=QMessageBox.Ok):
        self.parent = parent
        self.type = message_type
        self.message = message
        self.title = title
        if isinstance(buttons, QMessageBox.StandardButton):  # Для одиночного флага
            self.buttons = buttons
        elif isinstance(buttons, QMessageBox.StandardButtons):  # Для комбинации флагов
            self.buttons = int(buttons)  # <-- Вот ключевое изменение
        else:
            self.buttons = int(buttons)  # На всякий случай, если это уже int или что-то ещё
        self.style_path = get_path('user_settings', 'color_settings.json')
        self.style_manager = ApplyColor(self)
        self.styles = self.style_manager.load_styles()
        self.result = None
        self.main = None
        self.container = None
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        sound = {
            'info': winsound.MB_ICONASTERISK,
            'warning': winsound.MB_ICONEXCLAMATION,
            'error': winsound.MB_ICONHAND,
            'question': winsound.MB_ICONASTERISK
        }.get(self.type, winsound.MB_ICONASTERISK)
        winsound.MessageBeep(sound)

        self.main = QDialog(self.parent) if self.parent else QDialog()
        self.main.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.main.setAttribute(Qt.WA_TranslucentBackground)
        self.main.setFixedSize(300, 200)

        screen_geometry = self.main.screen().availableGeometry()
        self.main.move(
            (screen_geometry.width() - self.main.width()) // 2,
            (screen_geometry.height() - self.main.height()) // 2
        )

        self.container = QWidget(self.main)
        self.container.setObjectName("MessageContainer")
        # Отступы по 1 пикселю для создания бордера
        self.container.setGeometry(0, 0, self.main.width(), self.main.height())

        # Основной layout для всего контента
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(1, 1, 1, 1)  # Изменено с (0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Панель заголовка
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(35)
        title_bar.setGeometry(1, 1, self.main.width() - 2, 34)
        # Скругление только для верхней части
        title_bar.setStyleSheet("""
            #TitleBar {
                border-top-left-radius: 26px;
                border-top-right-radius: 26px;
            }
        """)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(5)

        title_label = QLabel(self.title)
        title_label.setStyleSheet("background: transparent;")
        title_label.setObjectName("TitleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseButton")
        close_btn.setFixedSize(20, 20)

        close_btn.clicked.connect(self.main.reject)
        title_layout.addWidget(close_btn)
        title_layout.addSpacing(7)

        main_layout.addWidget(title_bar)

        # Область содержимого (сообщение + кнопки)
        content_widget = QWidget()
        content_widget.setObjectName("ContentWidget")
        content_widget.setGeometry(
            1,  # X: 1px от левого края
            36,  # Y: 1px бордер + 35px заголовка
            self.main.width() - 2,  # Ширина минус бордер
            self.main.height() - 36 - 45  # Высота: общая - заголовок - место для кнопок
        )
        content_widget.setStyleSheet("""
            #ContentWidget {
                border-bottom-left-radius: 26px;
                border-bottom-right-radius: 26px;

            }
        """)
        content_layout = QVBoxLayout(content_widget)

        # Текст сообщения
        message_label = QLabel(self.message)
        message_label.setObjectName("MessageLabel")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet("background: transparent;")
        content_layout.addWidget(message_label)

        # --- Добавление кнопок ---
        if not hasattr(self, 'button_layout'):
            self.button_layout = QHBoxLayout()  # Убедиться, что атрибут существует
        self.button_layout.setContentsMargins(0, 0, 0, 10)
        self.button_layout.setSpacing(10)

        self.create_buttons()

        content_layout.addLayout(self.button_layout)

        main_layout.addWidget(content_widget)

    def create_buttons(self):
        """Создание кнопок в зависимости от переданных параметров"""
        while self.button_layout.count():
            item = self.button_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        button_map = {
            QMessageBox.Ok: "OK",
            QMessageBox.Cancel: "Отмена",
            QMessageBox.Yes: "Да",
            QMessageBox.No: "Нет",
            QMessageBox.Abort: "Прервать",
            QMessageBox.Retry: "Повторить",
            QMessageBox.Ignore: "Игнорировать"
        }

        button_added = False
        # Обработка комбинаций кнопок
        if isinstance(self.buttons, int):
            button_flags = [
                QMessageBox.Ok, QMessageBox.Cancel, QMessageBox.Yes,
                QMessageBox.No, QMessageBox.Abort, QMessageBox.Retry,
                QMessageBox.Ignore
            ]

            for flag in button_flags:
                if self.buttons & flag:
                    button_text = button_map.get(flag, "")
                    if button_text:
                        btn = QPushButton(button_text)
                        btn.setObjectName("DialogButton")
                        btn.setFixedSize(80, 30)
                        # Сохраняем флаг в локальной переменной для лямбды
                        flag_value = flag
                        connection = btn.clicked.connect(lambda checked, f=flag_value: self.button_clicked(f))
                        self.button_layout.addWidget(btn)
                        button_added = True

        # Если ни одна кнопка не была добавлена, добавляем OK по умолчанию
        if not button_added:
            btn = QPushButton("OK")
            btn.setObjectName("DialogButton")
            btn.setFixedSize(80, 30)  # Фиксированный размер

            btn.clicked.connect(lambda checked: self.button_clicked(QMessageBox.Ok))
            self.button_layout.addWidget(btn)

    def button_clicked(self, button_role):
        """Обработка нажатия кнопки"""
        self.main.done(button_role)

    def apply_styles(self):
        try:
            self.styles = self.style_manager.load_styles()

            # Применяем стили к текущему окну (если они есть в файле стилей)
            style_sheet = ""
            for widget, styles in self.styles.items():
                if widget.startswith("Q"):  # Для стандартных виджетов
                    selector = widget
                else:  # Для виджетов с objectName
                    selector = f"#{widget}"

                style_sheet += f"{selector} {{\n"
                for prop, value in styles.items():
                    style_sheet += f"    {prop}: {value};\n"
                style_sheet += "}\n"
            # Устанавливаем стиль для главного окна
            self.main.setStyleSheet(style_sheet)

        except Exception as e:
            debug_logger.error(f"Ошибка в методе apply_styles: {e}")

    def exec_(self):
        """Показать диалог и вернуть результат"""
        result = self.main.exec_()
        return result

    def show(self):
        """Показать диалог без ожидания результата"""
        self.main.show()
