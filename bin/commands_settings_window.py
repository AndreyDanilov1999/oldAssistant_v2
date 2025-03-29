import json
import os
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QFileDialog, QPushButton, QLineEdit, QLabel, QComboBox, \
    QVBoxLayout, QWidget, QDialog, QFrame, QStackedWidget, QHBoxLayout, QListWidget, QListWidgetItem, \
    QInputDialog, QSizePolicy

from bin.func_list import search_links
from logging_config import logger
from path_builder import get_path


class CommandSettingsWindow(QDialog):
    """
    Основное окно настроек команд и прочих опций
    """
    commands_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.assistant = parent
        self.left_column = None
        self.right_column = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Настройки")
        self.setFixedSize(700, 600)

        # Основной layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # Контейнер для левой колонки (будет прижат к верху)
        left_column_container = QWidget()
        left_column_container.setFixedWidth(200)

        # Вертикальный layout для левой колонки
        self.left_column = QVBoxLayout(left_column_container)
        self.left_column.setAlignment(Qt.AlignTop)  # Выравнивание по верху
        self.left_column.setContentsMargins(5, 5, 5, 5)
        self.left_column.setSpacing(10)

        # Добавляем растягивающий элемент внизу
        self.left_column.addStretch()

        main_layout.addWidget(left_column_container)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Правая колонка с содержимым
        self.right_column = QStackedWidget()
        main_layout.addWidget(self.right_column)

        # Добавляем вкладки
        self.add_tab("Создание команд", CreateCommandsWidget(self.assistant))
        self.add_tab("Ваши Команды", CommandsWidget(self.assistant))
        self.add_tab("Процессы ярлыков", ProcessLinksWidget(self.assistant))

    def add_tab(self, button_name, content_widget):
        button = QPushButton(button_name, self)
        button.setFixedHeight(30)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Вставляем кнопку перед растягивающим элементом
        self.left_column.insertWidget(self.left_column.count() - 1, button)
        self.right_column.addWidget(content_widget)

        button.clicked.connect(lambda _, w=content_widget:
                               self.right_column.setCurrentWidget(w))

class CreateCommandsWidget(QWidget):
    """
    Виджет создания команд с динамическим отображением форм
    """

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
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

    def create_forms(self):
        """Создаем все формы заранее"""
        # Форма для ярлыка
        self.shortcut_form = AppCommandForm(self.assistant)
        self.form_container.addWidget(self.shortcut_form)

        # Форма для папки
        self.folder_form = FolderCommandForm(self.assistant)
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
    """Форма для создания команды ярлыка"""

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.commands = self.assistant.load_commands()
        search_links()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.addStretch()

        # Поле для ввода команды
        self.key_input = QLineEdit(self)
        self.key_input.setPlaceholderText("Введите команду (например: 'браузер')")
        layout.addWidget(QLabel("Команда (уникальное слово):"))
        layout.addWidget(self.key_input)

        # Выбор ярлыка
        self.shortcut_combo = QComboBox(self)
        self.load_shortcuts()
        layout.addWidget(QLabel("Выберите ярлык:"))
        layout.addWidget(self.shortcut_combo)

        # Кнопка применения
        self.apply_button = QPushButton("Добавить команду", self)
        self.apply_button.clicked.connect(self.apply_command)
        layout.addWidget(self.apply_button)

    def load_shortcuts(self):
        """Загружает список ярлыков"""
        links_file = get_path('user_settings', 'links.json')
        try:
            with open(links_file, 'r', encoding='utf-8') as file:
                links = json.load(file)
                self.shortcut_combo.addItems(list(links.keys()))
        except Exception as e:
            logger.error(f"Ошибка загрузки ярлыков: {e}")

    def apply_command(self):
        """Добавляет новую команду"""
        key = self.key_input.text().strip().lower()
        selected = self.shortcut_combo.currentText()

        # Проверка на пустую команду
        if not key:
            self.assistant.show_message("Команда не может быть пустой!", "Предупреждение", "warning")
            return

        # Проверка на существующую команду
        if key in self.commands:
            self.assistant.show_message(f"Команда '{key}' уже существует!", "Предупреждение", "warning")
            return

        # Проверка на выбранный ярлык
        if not selected:
            self.assistant.show_message("Пожалуйста, выберите ярлык из списка!", "Предупреждение", "warning")
            return

        self.commands[key] = selected
        self.save_commands()

        # Обновляем команды в родительском классе
        self.assistant.commands = self.assistant.load_commands()

        # Отправляем сигнал обновления
        if hasattr(self.parent(), 'commands_updated'):
            self.parent().commands_updated.emit()

        self.assistant.show_message(f"Команда '{key}' добавлена!")
        self.key_input.clear()

    def save_commands(self):
        """Сохраняет команды в файл"""
        try:
            path = get_path('user_settings', 'commands.json')
            with open(path, 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения команд: {e}")


class FolderCommandForm(QWidget):
    """Форма для создания команды папки"""

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.commands = self.assistant.load_commands()
        search_links()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.addStretch()

        # Поле для ввода команды
        self.key_input = QLineEdit(self)
        self.key_input.setPlaceholderText("Введите команду (например: 'загрузки')")
        layout.addWidget(QLabel("Команда (уникальное слово):"))
        layout.addWidget(self.key_input)

        # Поле для выбора папки
        self.folder_path = QLineEdit(self)
        layout.addWidget(QLabel("Путь к папке:"))
        layout.addWidget(self.folder_path)

        # Кнопка выбора папки
        select_button = QPushButton("Выбрать папку...", self)
        select_button.clicked.connect(self.select_folder)
        layout.addWidget(select_button)

        # Кнопка применения
        self.apply_button = QPushButton("Добавить команду", self)
        self.apply_button.clicked.connect(self.apply_command)
        layout.addWidget(self.apply_button)

    def select_folder(self):
        """Открывает диалог выбора папки"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.folder_path.setText(folder)

    def apply_command(self):
        """Добавляет новую команду для папки"""
        key = self.key_input.text().strip().lower()
        folder = self.folder_path.text().strip()

        if not key or not folder:
            self.assistant.show_message("Заполните все поля!", "Предупреждение", "warning")
            return

        if key in self.commands:
            self.assistant.show_message(f"Команда '{key}' уже существует!", "Предупреждение", "warning")
            return

        if not self.folder_path.text().strip():
            self.assistant.show_message("Пожалуйста, укажите папку!", "Предупреждение", "warning")
            return

        self.commands[key] = folder
        self.save_commands()
        # Обновляем команды в родительском классе
        self.assistant.commands = self.assistant.load_commands()
        # Отправляем сигнал обновления
        if hasattr(self.parent(), 'commands_updated'):
            self.parent().commands_updated.emit()
        self.assistant.show_message(f"Команда '{key}' добавлена!")
        self.key_input.clear()
        self.folder_path.clear()

    def save_commands(self):
        """Сохраняет команды в файл"""
        try:
            path = get_path('user_settings', 'commands.json')
            with open(path, 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения команд: {e}")


class CommandsWidget(QWidget):
    """ Класс для обработки окна "Добавленные функции" """

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant  # Сохраняем ссылку на родительский класс
        self.commands = self.assistant.commands  # Доступ к командам родителя
        self.init_ui()
        self.update_commands_list()  # Обновляем список команд при инициализации

        # Подписываемся на сигнал обновления
        if hasattr(parent, 'commands_updated'):
            parent.commands_updated.connect(self.on_commands_updated)

    def on_commands_updated(self):
        """Обработчик обновления команд"""
        self.commands = self.assistant.commands  # Обновляем ссылку
        self.update_commands_list()  # Перерисовываем список

    def init_ui(self):
        self.setWindowTitle("Добавленные команды")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        self.commands_list = QListWidget(self)
        layout.addWidget(self.commands_list)

        # Кнопка "Удалить"
        self.delete_button = QPushButton("Удалить выбранную команду", self)
        self.delete_button.clicked.connect(self.delete_command)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def load_commands_from_file(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.warning(f"Файл {filename} не найден. Создаём новый файл.")
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump({}, file)  # Создаём пустой JSON
            return {}
        except json.JSONDecodeError:
            logger.error("Ошибка: файл содержит некорректный JSON.")
            self.assistant.show_message("Ошибка в формате файла JSON.", "Ошибка", "error")
            return {}

    def update_commands_list(self):
        """Обновляет список команд в QListWidget, загружая их из файла."""
        self.commands_list.clear()  # Очищаем текущий список
        # Загружаем команды из файла
        commands_file = get_path('user_settings', 'commands.json')  # Полный путь к файлу
        self.commands = self.load_commands_from_file(commands_file)

        if not isinstance(self.commands, dict):
            logger.error("Файл JSON не содержит словарь.")
            self.assistant.show_message("Файл JSON имеет некорректный формат.", "Ошибка", "error")
            self.commands = {}  # Сбрасываем команды

        for key, value in self.commands.items():
            # Создаем строку для отображения в QListWidget
            item_text = f"{key} : {value}"  # Теперь value - это просто строка
            try:
                item = QListWidgetItem(item_text)  # Создаем элемент
                self.commands_list.addItem(item)  # Добавляем элемент в QListWidget
            except Exception as e:
                logger.error(f"Ошибка при добавлении элемента: {e}")

    def delete_command(self):
        """Удаляет команду по выбранному ключу и соответствующий кортеж из process_names.json."""
        selected_items = self.commands_list.selectedItems()  # Получаем выбранные элементы

        if not selected_items:
            self.assistant.show_message("Пожалуйста, выберите команду для удаления.", "Предупреждение", "warning")
            return  # Если ничего не выбрано, выходим

        for item in selected_items:
            key = item.text().split(" : ")[0]  # Получаем ключ команды из текста элемента
            if key in self.commands:
                # Получаем значение (ярлык или путь) удаляемой команды
                value = self.commands[key]
                del self.commands[key]  # Удаляем команду из словаря
                self.commands_list.takeItem(self.commands_list.row(item))  # Удаляем элемент из QListWidget
                # Удаляем соответствующий кортеж из process_names.json
                process_names_file = get_path('user_settings', 'process_names.json')
                try:
                    with open(process_names_file, 'r', encoding='utf-8') as file:
                        process_names = json.load(file)
                    # Удаляем запись, если её ключ совпадает со значением удаляемой команды
                    updated_process_names = [entry for entry in process_names if list(entry.keys())[0] != value]
                    with open(process_names_file, 'w', encoding='utf-8') as file:
                        json.dump(updated_process_names, file, ensure_ascii=False, indent=4)

                except IOError as e:
                    logger.error(f"Ошибка при работе с файлом {process_names_file}: {e}")
                    self.assistant.show_message(f"Не удалось обновить process_names.json: {e}", "Ошибка", "error")
        self.save_commands()  # Сохраняем изменения в commands.json

    def save_commands(self):
        """Сохраняет команды в файл commands.json."""
        commands_file = get_path('user_settings', 'commands.json')  # Полный путь к файлу
        try:
            with open(commands_file, 'w', encoding='utf-8') as file:
                json.dump(self.commands, file, ensure_ascii=False, indent=4)
                logger.info("Список команд обновлён.")
        except IOError as e:
            logger.error(f"Ошибка записи в файл {commands_file}: {e}")
            self.assistant.show_message("Не удалось сохранить команды.", "Ошибка", "error")

    def showEvent(self, event):
        """Обновляем список при каждом показе виджета"""
        self.update_commands_list()
        super().showEvent(event)


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
        process_name, ok = QInputDialog.getText(self, "Добавить процесс", "Введите название процесса:")
        if ok and process_name:
            for item in self.process_names:
                if link_name in item:
                    if process_name not in item[link_name]:
                        item[link_name].append(process_name)
                        self.update_processes_list(link_name)
                        self.save_process_names()
                    else:
                        self.assistant.show_message("Процесс с таким именем уже существует.", "Ошибка", "error")
                    break

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

    def closeEvent(self, event):
        """ Сохраняет данные при закрытии окна """
        self.save_process_names()
        super().closeEvent(event)