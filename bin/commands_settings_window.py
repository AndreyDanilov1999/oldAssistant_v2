import json
import os
from PyQt5.QtCore import pyqtSignal, Qt, QStringListModel, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QFileDialog, QPushButton, QLineEdit, QLabel, QComboBox, \
    QVBoxLayout, QWidget, QDialog, QFrame, QStackedWidget, QHBoxLayout, QListWidget, QListWidgetItem, \
    QInputDialog, QSizePolicy, QCompleter, QDialogButtonBox, QMessageBox
from bin.func_list import search_links, scan_and_copy_shortcuts
from logging_config import logger, debug_logger
from path_builder import get_path


class CommandSettingsWindow(QDialog):
    """
    Окно настроек команд с анимацией появления/исчезания
    """
    commands_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.current_commands = parent.commands.copy() if hasattr(parent,
                                                                  'commands') else {}  # Центральное хранилище команд
        self.load_commands()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(parent.width(), parent.height())
        self.setAttribute(Qt.WA_TranslucentBackground)  # Для эффектов прозрачности

        # Анимация прозрачности
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(300)

        self.init_ui()
        self.setup_animation()

    def setup_animation(self):
        # Позиционируем по центру родительского окна
        parent_center = self.assistant.geometry().center()
        self.move(parent_center.x() - self.width() // 2,
                  parent_center.y() - self.height() // 2)

    def init_ui(self):
        # Главный контейнер
        self.container = QWidget(self)
        self.container.setObjectName("SettingsContainer")
        self.container.setGeometry(0, 0, self.width(), self.height() - 120)

        # Кастомный заголовок
        self.title_bar = QWidget(self.container)
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setGeometry(0, 0, self.container.width(), 35)
        self.title_bar_layout = QHBoxLayout(self.title_bar)
        self.title_bar_layout.setContentsMargins(10, 5, 10, 5)

        self.title_label = QLabel("Настройки команд")
        self.title_bar_layout.addWidget(self.title_label)
        self.title_bar_layout.addStretch()

        self.close_btn = QPushButton("✕", self.title_bar)
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.clicked.connect(self.hide_with_animation)
        self.title_bar_layout.addWidget(self.close_btn)

        # Основной layout под заголовком
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 40, 0, 0)  # Отступ под заголовком
        self.container.setLayout(main_layout)

        # Левая панель с кнопками
        self.tabs_container = QWidget()
        self.tabs_container.setFixedWidth(200)
        self.tabs_container.setObjectName("TabsContainer")

        self.tabs_layout = QVBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(5, 15, 5, 10)
        self.tabs_layout.setSpacing(5)
        self.tabs_layout.setAlignment(Qt.AlignTop)

        # Правая панель с контентом
        self.right_column = QStackedWidget()
        self.right_column.setObjectName("ContentStack")

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)

        # Компоновка
        main_layout.addWidget(self.tabs_container)
        main_layout.addWidget(separator)
        main_layout.addWidget(self.right_column)

        # Добавляем вкладки
        self.add_tab("Создание команд", CreateCommandsWidget(self.assistant, self))
        self.add_tab("Ваши Команды", CommandsWidget(self.assistant, self))
        self.add_tab("Процессы ярлыков", ProcessLinksWidget(self.assistant))

    def keyPressEvent(self, event):
        """Переопределяем обработку нажатия клавиш"""
        if event.key() == Qt.Key_Escape:
            # Только Escape закрывает окно
            if self.opacity_animation.state() != QPropertyAnimation.Running:
                self.hide_with_animation()
            event.accept()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Игнорируем Enter, чтобы он не закрывал диалог
            event.ignore()
        else:
            super().keyPressEvent(event)

    def add_tab(self, button_name, content_widget):
        button = QPushButton(button_name)
        button.setFixedHeight(30)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if button_name == "Ваши Команды":
            self.commands_widget = content_widget
            self.commands_updated.connect(self.commands_widget.on_commands_updated)

        self.tabs_layout.addWidget(button)
        self.right_column.addWidget(content_widget)
        button.clicked.connect(lambda: self.right_column.setCurrentWidget(content_widget))

    def showEvent(self, event):
        """Анимация появления"""
        self.setWindowOpacity(0.0)
        self.raise_()

        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()

        super().showEvent(event)

    def hide_with_animation(self):
        """Анимация исчезания"""
        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.finished.connect(self.hide)
        self.opacity_animation.start()

    def hideEvent(self, event):
        """Сброс состояния"""
        self.opacity_animation.finished.disconnect(self.hide)
        self.setWindowOpacity(1.0)
        super().hideEvent(event)

    def load_commands(self):
        """Централизованная загрузка команд"""
        try:
            path = get_path('user_settings', 'commands.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as file:
                    self.current_commands = json.load(file)
            else:
                self.current_commands = {}
        except Exception as e:
            logger.error(f"Ошибка загрузки команд: {e}")
            self.current_commands = {}

    def save_commands(self):
        """Централизованное сохранение команд с уведомлением"""
        try:
            path = get_path('user_settings', 'commands.json')
            with open(path, 'w', encoding='utf-8') as file:
                json.dump(self.current_commands, file, ensure_ascii=False, indent=4)

            if hasattr(self.assistant, 'commands'):
                self.assistant.commands = self.current_commands.copy()

            self.load_commands()
        except Exception as e:
            logger.error(f"Ошибка сохранения команд: {e}")

    def handle_commands_change(self, new_commands):
        """Обработчик изменений из дочерних виджетов"""
        self.current_commands = new_commands
        self.save_commands()  # Будет испущен сигнал commands_updated

class CreateCommandsWidget(QWidget):
    """
    Виджет создания команд с динамическим отображением форм
    """

    def __init__(self, assistant, settings_window, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.settings_window = settings_window
        self.current_form = None  # Текущая активная форма
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel("Для чего создаем команду?")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Контейнер для кнопок выбора типа
        btn_layout = QHBoxLayout()

        # Кнопка для создания команды ярлыка
        self.btn_shortcut = QPushButton("Для ярлыка")
        self.btn_shortcut.setCheckable(True)
        self.btn_shortcut.clicked.connect(self.show_shortcut_form)
        btn_layout.addWidget(self.btn_shortcut)

        # Кнопка для создания команды папки
        self.btn_folder = QPushButton("Для папки")
        self.btn_folder.setCheckable(True)
        self.btn_folder.clicked.connect(self.show_folder_form)
        btn_layout.addWidget(self.btn_folder)

        layout.addLayout(btn_layout)

        # Контейнер для динамических форм
        self.form_container = QStackedWidget()
        self.form_container.hide()
        layout.addWidget(self.form_container)

        # Создаем формы (но пока не добавляем в layout)
        self.create_forms()

        layout.addStretch()

        self.search_btn = QPushButton("Автопоиск ярлыков")
        self.search_btn.clicked.connect(self.autosearch_shortcuts)
        layout.addWidget(self.search_btn)

    def autosearch_shortcuts(self):
        """Поиск ярлыков в стандартном расположении"""
        scan_and_copy_shortcuts()
        search_links()
        self.assistant.show_message(f"Поиск завершен!")

        # Обновляем список в форме
        if hasattr(self.shortcut_form, 'refresh_shortcuts'):
            self.shortcut_form.refresh_shortcuts()

        # Отправляем сигнал об обновлении команд
        if hasattr(self.parent(), 'commands_updated'):
            self.parent().commands_updated.emit()

    def create_forms(self):
        """Создаем все формы заранее"""
        # Форма для ярлыка
        self.shortcut_form = AppCommandForm(self.assistant, self.settings_window)
        self.form_container.addWidget(self.shortcut_form)

        # Форма для папки
        self.folder_form = FolderCommandForm(self.assistant, self.settings_window)
        self.form_container.addWidget(self.folder_form)

        # Изначально скрываем все формы
        self.form_container.setCurrentIndex(-1)

    def show_shortcut_form(self):
        """Показывает форму для создания команды ярлыка"""
        self.btn_shortcut.setChecked(True)
        self.btn_folder.setChecked(False)
        self.form_container.show()
        self.form_container.setCurrentWidget(self.shortcut_form)

    def show_folder_form(self):
        """Показывает форму для создания команды папки"""
        self.btn_folder.setChecked(True)
        self.btn_shortcut.setChecked(False)
        self.form_container.show()
        self.form_container.setCurrentWidget(self.folder_form)


class AppCommandForm(QWidget):
    def __init__(self, assistant, settings_window, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.settings_window = settings_window
        search_links()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.addStretch()

        self.key_input = QLineEdit(self)
        self.key_input.setPlaceholderText("Введите команду (например: 'браузер')")
        self.key_input.returnPressed.connect(self.apply_command)  # Обработка нажатия Enter
        layout.addWidget(QLabel("Команда (уникальное слово):"))
        layout.addWidget(self.key_input)

        self.shortcut_combo = SearchComboBox(self)
        self.load_shortcuts()
        self.shortcut_combo.lineEdit().returnPressed.connect(self.apply_command)  # Обработка нажатия Enter
        layout.addWidget(QLabel("Выберите ярлык:"))
        layout.addWidget(self.shortcut_combo)

        self.apply_button = QPushButton("Добавить команду", self)
        self.apply_button.clicked.connect(self.apply_command)
        layout.addWidget(self.apply_button)

    def load_shortcuts(self):
        links_file = get_path('user_settings', 'links.json')
        try:
            with open(links_file, 'r', encoding='utf-8') as file:
                links = json.load(file)
                self.shortcut_combo.updateModel(links)
        except Exception as e:
            logger.error(f"Ошибка загрузки ярлыков: {e}")

    def refresh_shortcuts(self):
        current_selection = self.shortcut_combo.currentText()
        links_file = get_path('user_settings', 'links.json')
        try:
            with open(links_file, 'r', encoding='utf-8') as file:
                links = json.load(file)
                self.shortcut_combo.updateModel(links)
                if current_selection in links:
                    self.shortcut_combo.setCurrentText(current_selection)
        except Exception as e:
            logger.error(f"Ошибка загрузки ярлыков: {e}")

    def apply_command(self):
        key = self.key_input.text().strip().lower()
        selected_name = self.shortcut_combo.currentFileName()

        if not key:
            self.assistant.show_message("Команда не может быть пустой!", "Предупреждение", "warning")
            return

        if key in self.settings_window.current_commands:
            self.assistant.show_message(f"Команда '{key}' уже существует!", "Предупреждение", "warning")
            return

        if not selected_name:
            self.assistant.show_message("Пожалуйста, выберите ярлык из списка!", "Предупреждение", "warning")
            return

        self.settings_window.current_commands[key] = selected_name
        self.settings_window.save_commands()
        self.settings_window.commands_updated.emit(self.settings_window.current_commands)
        self.assistant.show_notification_message(message=f"Команда '{key}' добавлена!")
        self.key_input.clear()


class FolderCommandForm(QWidget):
    def __init__(self, assistant, settings_window, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.settings_window = settings_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.addStretch()

        self.key_input = QLineEdit(self)
        self.key_input.setPlaceholderText("Введите команду (например: 'загрузки')")
        self.key_input.returnPressed.connect(self.apply_command)  # Обработка нажатия Enter
        layout.addWidget(QLabel("Команда (уникальное слово):"))
        layout.addWidget(self.key_input)

        self.folder_path = QLineEdit(self)
        self.folder_path.returnPressed.connect(self.apply_command)  # Обработка нажатия Enter
        layout.addWidget(QLabel("Путь к папке:"))
        layout.addWidget(self.folder_path)

        select_button = QPushButton("Выбрать папку...", self)
        select_button.clicked.connect(self.select_folder)
        layout.addWidget(select_button)

        self.apply_button = QPushButton("Добавить команду", self)
        self.apply_button.clicked.connect(self.apply_command)
        layout.addWidget(self.apply_button)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.folder_path.setText(folder)

    def apply_command(self):
        key = self.key_input.text().strip().lower()
        folder = self.folder_path.text().strip()

        if not key or not folder:
            self.assistant.show_message("Заполните все поля!", "Предупреждение", "warning")
            return

        if key in self.settings_window.current_commands:
            self.assistant.show_message(f"Команда '{key}' уже существует!", "Предупреждение", "warning")
            return

        self.settings_window.current_commands[key] = folder
        self.settings_window.save_commands()
        self.settings_window.commands_updated.emit(self.settings_window.current_commands)
        self.assistant.show_notification_message(message=f"Команда '{key}' добавлена!")
        self.key_input.clear()
        self.folder_path.clear()


class CommandsWidget(QWidget):
    """Класс для обработки окна 'Добавленные команды'"""

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.parent_window = parent
        self.commands = {}
        self.init_ui()
        self.load_initial_commands()

        # Подключаем сигнал обновления команд
        if hasattr(parent, 'commands_updated'):
            parent.commands_updated.connect(self.on_commands_updated)

    def load_initial_commands(self):
        """Первоначальная загрузка команд"""
        self.commands = self.load_commands_from_file(get_path('user_settings', 'commands.json'))
        self.update_commands_list()

    def on_commands_updated(self, new_commands):
        """Обработчик обновления команд (принимает словарь новых команд)"""
        self.commands = new_commands.copy()
        self.update_commands_list()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("Добавленные команды")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        self.commands_list = QListWidget(self)
        self.commands_list.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.commands_list)

        self.delete_button = QPushButton("Удалить выбранную команду", self)
        self.delete_button.clicked.connect(self.delete_command)
        layout.addWidget(self.delete_button)

    def showEvent(self, event):
        """Переопределяем метод показа виджета"""
        super().showEvent(event)
        self.select_last_item()

    def select_last_item(self):
        """Выбирает последний элемент в списке"""
        if self.commands_list.count() > 0:
            last_index = self.commands_list.count() - 1
            self.commands_list.setCurrentRow(last_index)
            self.commands_list.scrollToBottom()

    def update_commands_list(self):
        """Обновляет список команд"""
        self.commands_list.clear()

        if not isinstance(self.commands, dict):
            logger.error("Команды должны быть словарем")
            self.assistant.show_message("Некорректный формат команд", "Ошибка", "error")
            return

        for key, value in self.commands.items():
            item_text = f"{key} : {value}"
            item = QListWidgetItem(item_text)
            self.commands_list.addItem(item)

        self.select_last_item()

    def load_commands_from_file(self, filename):
        """Загрузка команд из файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.warning(f"Файл {filename} не найден, создаем новый")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Ошибка в формате файла {filename}")
            self.assistant.show_message("Ошибка в формате JSON", "Ошибка", "error")
            return {}

    def delete_command(self):
        """Удаление выбранной команды"""
        selected_items = self.commands_list.selectedItems()
        if not selected_items:
            self.assistant.show_message("Выберите команду для удаления", "Предупреждение", "warning")
            return

        # Удаляем выбранные команды
        for item in selected_items:
            key = item.text().split(" : ")[0]
            if key in self.commands:
                self.remove_command_from_process_names(self.commands[key])
                del self.commands[key]
                self.commands_list.takeItem(self.commands_list.row(item))

        self.save_commands()
        self.select_last_item()

    def remove_command_from_process_names(self, command_value):
        """Удаляет команду из process_names.json"""
        process_names_file = get_path('user_settings', 'process_names.json')
        try:
            with open(process_names_file, 'r', encoding='utf-8') as file:
                process_names = json.load(file)

            updated_names = [entry for entry in process_names if list(entry.keys())[0] != command_value]

            with open(process_names_file, 'w', encoding='utf-8') as file:
                json.dump(updated_names, file, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка при обновлении process_names.json: {e}")

    def save_commands(self):
        """Только сохраняет команды, НЕ испускает сигнал"""
        try:
            with open(get_path('user_settings', 'commands.json'), 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=4)

            # Просим родительское окно обработать обновление
            if hasattr(self.parent_window, 'handle_commands_change'):
                self.parent_window.handle_commands_change(self.commands)

        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")


class ProcessLinksWidget(QWidget):
    """ Класс для обработки окна "Процессы ярлыков" """

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.process_names_path = self.assistant.process_names
        self.process_names = self.load_process_names()
        self.init_ui()

    def init_ui(self):
        """ Инициализация пользовательского интерфейса """
        self.setWindowTitle("Процессы ярлыков")

        # Основной вертикальный макет
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Заголовок
        title = QLabel("Список процессов, привязанных к ярлыку\n(нужны для закрытия)")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title)

        # Горизонтальный макет для левой и правой колонок
        content_layout = QHBoxLayout()

        # Левая колонка: список ярлыков
        left_layout = QVBoxLayout()
        self.processes_label = QLabel("Ярлыки")
        left_layout.addWidget(self.processes_label)
        self.links_list = QListWidget()
        self.links_list.itemClicked.connect(self.on_link_selected)
        left_layout.addWidget(self.links_list)

        # Правая колонка: список процессов
        right_layout = QVBoxLayout()
        self.processes_label = QLabel("Список процессов")
        right_layout.addWidget(self.processes_label)

        self.processes_list = QListWidget()
        right_layout.addWidget(self.processes_list)

        # Кнопки для управления процессами
        self.add_process_button = QPushButton("Добавить процесс")
        self.add_process_button.clicked.connect(self.add_process)
        right_layout.addWidget(self.add_process_button)

        self.remove_process_button = QPushButton("Удалить процесс")
        self.remove_process_button.clicked.connect(self.remove_process)
        right_layout.addWidget(self.remove_process_button)

        # Добавляем левую и правую части в горизонтальный макет
        content_layout.addLayout(left_layout, 1)
        content_layout.addLayout(right_layout, 2)

        # Добавляем горизонтальный макет в основной вертикальный макет
        main_layout.addLayout(content_layout)

        # Устанавливаем основной макет для окна
        self.setLayout(main_layout)

        # Заполняем список ярлыков
        self.update_links_list()

    def load_process_names(self):
        """ Загружает данные о ярлыках и процессах из файла process_names.json """
        if os.path.exists(self.process_names_path):
            with open(self.process_names_path, "r", encoding="utf-8") as file:
                return json.load(file)
        return []

    def save_process_names(self):
        """ Сохраняет данные о ярлыках и процессах в файл process_names.json """
        with open(self.process_names_path, "w", encoding="utf-8") as file:
            json.dump(self.process_names, file, ensure_ascii=False, indent=4)

    def update_links_list(self):
        """ Обновляет список ярлыков """
        self.links_list.clear()
        for item in self.process_names:
            for link_name in item.keys():
                self.links_list.addItem(link_name)

    def update_processes_list(self, link_name):
        """ Обновляет список процессов для выбранного ярлыка """
        self.processes_list.clear()
        for item in self.process_names:
            if link_name in item:
                for process in item[link_name]:
                    self.processes_list.addItem(process)
                break

    def on_link_selected(self, item):
        """ Обработка выбора ярлыка """
        link_name = item.text()
        self.update_processes_list(link_name)

    def add_process(self):
        """ Добавляет процесс к выбранному ярлыку """
        current_link = self.links_list.currentItem()
        if not current_link:
            self.assistant.show_message("Выберите ярлык для добавления процесса.", "Ошибка", "error")
            return

        link_name = current_link.text()
        self.add_custom_process(link_name)
        # process_name, ok = QInputDialog.getText(self, "Добавить процесс", "Введите название процесса:")
        # if ok and process_name:
        #     for item in self.process_names:
        #         if link_name in item:
        #             if process_name not in item[link_name]:
        #                 item[link_name].append(process_name)
        #                 self.update_processes_list(link_name)
        #                 self.save_process_names()
        #             else:
        #                 self.assistant.show_message("Процесс с таким именем уже существует.", "Ошибка", "error")
        #             break

    def remove_process(self):
        """ Удаляет процесс из выбранного ярлыка """
        current_link = self.links_list.currentItem()
        current_process = self.processes_list.currentItem()
        if not current_link or not current_process:
            self.assistant.show_message("Выберите ярлык и процесс для удаления.", "Ошибка", "error")
            return

        link_name = current_link.text()
        process_name = current_process.text()
        for item in self.process_names:
            if link_name in item:
                if process_name in item[link_name]:
                    item[link_name].remove(process_name)
                    self.update_processes_list(link_name)
                    self.save_process_names()
                break

    def add_custom_process(self, link_name):
        """Кастомный диалог для добавления нового процесса"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить процесс")
        dialog.setFixedSize(250, 100)

        layout = QVBoxLayout(dialog)

        # Поле ввода
        label = QLabel("Введите название процесса:")
        layout.addWidget(label)

        process_edit = QLineEdit()
        process_edit.setPlaceholderText("Название процесса...")
        layout.addWidget(process_edit)

        # Создаем кастомные кнопки
        button_box = QDialogButtonBox()

        # Кнопка Ок
        ok_button = QPushButton("Ок")
        ok_button.setStyleSheet("padding: 1px 10px;")
        ok_button.clicked.connect(dialog.accept)

        # Кнопка Закрыть
        close_button = QPushButton("Закрыть")
        close_button.setStyleSheet("padding: 1px 10px;")
        close_button.clicked.connect(dialog.reject)

        button_box.addButton(ok_button, QDialogButtonBox.AcceptRole)
        button_box.addButton(close_button, QDialogButtonBox.RejectRole)

        layout.addStretch()

        layout.addWidget(button_box)

        # Валидация ввода
        def validate_input():
            text = process_edit.text().strip()
            ok_button.setEnabled(bool(text))

        process_edit.textChanged.connect(validate_input)
        validate_input()  # Инициализация состояния кнопки

        # Проверка на дубликаты перед закрытием
        def check_and_accept():
            process_name = process_edit.text().strip()

            # Проверка на существующий процесс
            for item in self.process_names:
                if link_name in item:
                    if process_name in item[link_name]:
                        QMessageBox.warning(
                            self,
                            "Ошибка",
                            "Процесс с таким именем уже существует."
                        )
                        return

                    item[link_name].append(process_name)
                    self.update_processes_list(link_name)
                    self.save_process_names()
                    dialog.accept()
                    return

        ok_button.clicked.disconnect()
        ok_button.clicked.connect(check_and_accept)

        if dialog.exec() == QDialog.Accepted:
            process_edit.setFocus()

    def closeEvent(self, event):
        """ Сохраняет данные при закрытии окна """
        self.save_process_names()
        super().closeEvent(event)


class SearchComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)

        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.setCompleter(self.completer)
        self.setInsertPolicy(QComboBox.NoInsert)

        self._items_data = {}  # {filename: full_path}

    def updateModel(self, items_data):
        """Обновляет модель с данными {имя_файла: полный_путь}"""
        self._items_data = items_data
        self.clear()
        self.addItems(list(items_data.keys()))

        # Обновляем автодополнение
        model = QStringListModel(list(items_data.keys()))
        self.completer.setModel(model)

    def currentFileName(self):
        """Возвращает выбранное имя файла"""
        return self.currentText()

    def currentFilePath(self):
        """Возвращает полный путь выбранного файла"""
        return self._items_data.get(self.currentText(), "")




# class AppCommandForm(QWidget):
#     def __init__(self, assistant, settings_window, parent=None):
#         super().__init__(parent)
#         self.assistant = assistant
#         self.settings_window = settings_window
#         search_links()
#         self.init_ui()
#
#     def init_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(5, 5, 5, 5)
#         layout.setSpacing(5)
#         layout.addStretch()
#
#         self.key_input = QLineEdit(self)
#         self.key_input.setPlaceholderText("Введите команду (например: 'браузер')")
#         layout.addWidget(QLabel("Команда (уникальное слово):"))
#         layout.addWidget(self.key_input)
#
#         self.shortcut_combo = SearchComboBox(self)
#         self.load_shortcuts()
#         layout.addWidget(QLabel("Выберите ярлык:"))
#         layout.addWidget(self.shortcut_combo)
#
#         self.apply_button = QPushButton("Добавить команду", self)
#         self.apply_button.clicked.connect(self.apply_command)
#         layout.addWidget(self.apply_button)
#
#     def load_shortcuts(self):
#         links_file = get_path('user_settings', 'links.json')
#         try:
#             with open(links_file, 'r', encoding='utf-8') as file:
#                 links = json.load(file)
#                 self.shortcut_combo.updateModel(links)
#         except Exception as e:
#             logger.error(f"Ошибка загрузки ярлыков: {e}")
#
#     def refresh_shortcuts(self):
#         current_selection = self.shortcut_combo.currentText()
#         links_file = get_path('user_settings', 'links.json')
#         try:
#             with open(links_file, 'r', encoding='utf-8') as file:
#                 links = json.load(file)
#                 self.shortcut_combo.updateModel(links)
#                 if current_selection in links:
#                     self.shortcut_combo.setCurrentText(current_selection)
#         except Exception as e:
#             logger.error(f"Ошибка загрузки ярлыков: {e}")
#
#     def apply_command(self):
#         key = self.key_input.text().strip().lower()
#         selected_name = self.shortcut_combo.currentFileName()
#
#         if not key:
#             self.assistant.show_message("Команда не может быть пустой!", "Предупреждение", "warning")
#             return
#
#         if key in self.settings_window.current_commands:
#             self.assistant.show_message(f"Команда '{key}' уже существует!", "Предупреждение", "warning")
#             return
#
#         if not selected_name:
#             self.assistant.show_message("Пожалуйста, выберите ярлык из списка!", "Предупреждение", "warning")
#             return
#
#         self.settings_window.current_commands[key] = selected_name
#         self.settings_window.save_commands()
#         self.settings_window.commands_updated.emit(self.settings_window.current_commands)
#         self.assistant.show_message(f"Команда '{key}' добавлена!")
#         self.key_input.clear()


# class FolderCommandForm(QWidget):
#     def __init__(self, assistant, settings_window, parent=None):
#         super().__init__(parent)
#         self.assistant = assistant
#         self.settings_window = settings_window
#         self.init_ui()
#
#     def init_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(5, 5, 5, 5)
#         layout.setSpacing(5)
#         layout.addStretch()
#
#         self.key_input = QLineEdit(self)
#         self.key_input.setPlaceholderText("Введите команду (например: 'загрузки')")
#         layout.addWidget(QLabel("Команда (уникальное слово):"))
#         layout.addWidget(self.key_input)
#
#         self.folder_path = QLineEdit(self)
#         layout.addWidget(QLabel("Путь к папке:"))
#         layout.addWidget(self.folder_path)
#
#         select_button = QPushButton("Выбрать папку...", self)
#         select_button.clicked.connect(self.select_folder)
#         layout.addWidget(select_button)
#
#         self.apply_button = QPushButton("Добавить команду", self)
#         self.apply_button.clicked.connect(self.apply_command)
#         layout.addWidget(self.apply_button)
#
#     def select_folder(self):
#         folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
#         if folder:
#             self.folder_path.setText(folder)
#
#     def apply_command(self):
#         key = self.key_input.text().strip().lower()
#         folder = self.folder_path.text().strip()
#
#         if not key or not folder:
#             self.assistant.show_message("Заполните все поля!", "Предупреждение", "warning")
#             return
#
#         if key in self.settings_window.current_commands:
#             self.assistant.show_message(f"Команда '{key}' уже существует!", "Предупреждение", "warning")
#             return
#
#         self.settings_window.current_commands[key] = folder
#         self.settings_window.save_commands()
#         self.settings_window.commands_updated.emit(self.settings_window.current_commands)
#         self.assistant.show_message(f"Команда '{key}' добавлена!")
#         self.key_input.clear()
#         self.folder_path.clear()


# class CommandsWidget(QWidget):
#     def __init__(self, assistant, settings_window, parent=None):
#         super().__init__(parent)
#         self.assistant = assistant
#         self.settings_window = settings_window
#         self.init_ui()
#         self.update_commands_list()
#
#         self.settings_window.commands_updated.connect(self.on_commands_updated)
#
#     def on_commands_updated(self, commands):
#         self.update_commands_list()
#
#     def init_ui(self):
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(15, 15, 15, 15)
#         layout.setSpacing(20)
#
#         self.commands_list = QListWidget(self)
#         layout.addWidget(self.commands_list)
#
#         self.delete_button = QPushButton("Удалить выбранную команду", self)
#         self.delete_button.clicked.connect(self.delete_command)
#         layout.addWidget(self.delete_button)
#
#     def update_commands_list(self):
#         self.commands_list.clear()
#         for key, value in self.settings_window.current_commands.items():
#             self.commands_list.addItem(f"{key} : {value}")
#
#     def delete_command(self):
#         selected_items = self.commands_list.selectedItems()
#         if not selected_items:
#             self.assistant.show_message("Пожалуйста, выберите команду для удаления.", "Предупреждение", "warning")
#             return
#
#         for item in selected_items:
#             key = item.text().split(" : ")[0]
#             if key in self.settings_window.current_commands:
#                 del self.settings_window.current_commands[key]
#                 self.settings_window.save_commands()
#                 self.settings_window.commands_updated.emit(self.settings_window.current_commands)
#
#
