import json
import os
from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QFileDialog, QPushButton, QLineEdit, QLabel, QComboBox, \
    QVBoxLayout, QWidget, QDialog, QFrame, QStackedWidget, QHBoxLayout, QListWidget, QListWidgetItem, \
    QCompleter, QDialogButtonBox, QMessageBox
from bin.func_list import search_links, scan_and_copy_shortcuts
from bin.signals import commands_signal
from logging_config import debug_logger
from path_builder import get_path


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
        layout.setSpacing(15)

        # Заголовок
        title = QLabel("Для чего создаем команду?")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("background: transparent; font-size: 16px; font-weight: bold;")
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

        self.ps = QLabel("Внимание! Перед присвоением команды попробуйте сказать нужную фразу и "
                         "сверьте распознанный вариант в окне логов. (Инструкция во вкладке 'Гайды')")
        self.ps.setWordWrap(True)
        self.ps.setStyleSheet("background-color: transparent")
        layout.addWidget(self.ps)

        self.search_btn = QPushButton("Автопоиск ярлыков")
        self.search_btn.clicked.connect(self.autosearch_shortcuts)
        layout.addWidget(self.search_btn)

    def autosearch_shortcuts(self):
        """Поиск ярлыков в стандартном расположении"""
        scan_and_copy_shortcuts()
        search_links()
        self.assistant.show_notification_message(f"Поиск завершен!")

        # Обновляем список в форме
        if hasattr(self.shortcut_form, 'refresh_shortcuts'):
            self.shortcut_form.refresh_shortcuts()

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
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        search_links()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addStretch()

        self.key_input = QLineEdit(self)
        self.key_input.setPlaceholderText("Введите команду (например: 'браузер')")
        self.key_input.returnPressed.connect(self.apply_command)  # Обработка нажатия Enter

        # Label для ошибок
        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: red; font-size: 11px; background-color: transparent; height: 15px;")

        self.label_command = QLabel("Команда (уникальное слово):")
        self.label_command.setStyleSheet("background: transparent;")

        self.shortcut_combo = SearchComboBox(self)
        self.load_shortcuts()
        self.shortcut_combo.lineEdit().returnPressed.connect(self.apply_command)  # Обработка нажатия Enter
        self.label_link = QLabel("Выберите ярлык:")
        self.label_link.setStyleSheet("background: transparent;")

        self.apply_button = QPushButton("Добавить команду", self)
        self.apply_button.clicked.connect(self.apply_command)

        layout.addWidget(self.label_command)
        layout.addWidget(self.key_input)
        layout.addWidget(self.error_label)
        layout.addWidget(self.label_link)
        layout.addWidget(self.shortcut_combo)
        layout.addWidget(self.apply_button)

    def load_shortcuts(self):
        links_file = get_path('user_settings', 'links.json')
        try:
            with open(links_file, 'r', encoding='utf-8') as file:
                links = json.load(file)
                self.shortcut_combo.updateModel(links)
        except Exception as e:
            debug_logger.error(f"Ошибка загрузки ярлыков: {e}")

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
            debug_logger.error(f"Ошибка загрузки ярлыков: {e}")

    def apply_command(self):
        key = self.key_input.text().strip().lower()
        selected_name = self.shortcut_combo.currentFileName()

        if not key:
            self.show_error("Команда не может быть пустой!")
            return

        if key in self.assistant.commands:
            self.show_error(f"Команда '{key}' уже существует!")
            return

        if not selected_name:
            self.show_error("Пожалуйста, выберите ярлык из списка!")
            return

        self.assistant.commands[key] = selected_name
        commands_signal.commands_updated.emit()
        self.assistant.show_notification_message(message=f"Команда '{key}' добавлена!")
        self.key_input.clear()
        self.error_label_clear()

    def show_error(self, message):
        """Показывает сообщение об ошибке."""
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def error_label_clear(self):
        """Очистка лейбла ошибок"""
        self.error_label.setText("")
        self.error_label.setVisible(False)


class FolderCommandForm(QWidget):
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addStretch()

        self.key_input = QLineEdit(self)
        self.key_input.setPlaceholderText("Введите команду (например: 'загрузки')")
        self.key_input.returnPressed.connect(self.apply_command)  # Обработка нажатия Enter

        # Label для ошибок
        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: red; font-size: 11px; background-color: transparent; height: 15px;")

        self.label_command_folder = QLabel("Команда (уникальное слово):")
        self.label_command_folder.setStyleSheet("background: transparent;")

        choice_layout = QHBoxLayout()
        choice_layout.setSpacing(5)

        self.folder_path = QLineEdit(self)
        self.folder_path.returnPressed.connect(self.apply_command)  # Обработка нажатия Enter
        self.label_folder = QLabel("Путь к папке:")
        self.label_folder.setStyleSheet("background: transparent;")

        select_button = QPushButton("Обзор", self)
        select_button.setStyleSheet("padding-left: 6px; padding-right: 6px;")
        select_button.clicked.connect(self.select_folder)

        self.apply_button = QPushButton("Добавить команду", self)
        self.apply_button.clicked.connect(self.apply_command)

        layout.addWidget(self.label_command_folder)
        layout.addWidget(self.key_input)
        layout.addWidget(self.error_label)
        layout.addWidget(self.label_folder)
        choice_layout.addWidget(self.folder_path)
        choice_layout.addWidget(select_button)
        layout.addLayout(choice_layout)
        layout.addWidget(self.apply_button)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.folder_path.setText(folder)

    def apply_command(self):
        key = self.key_input.text().strip().lower()
        folder = self.folder_path.text().strip()

        if not key or not folder:
            self.show_error("Заполните все поля!")
            return

        if key in self.assistant.commands:
            self.show_error(f"Команда '{key}' уже существует!")
            return

        self.assistant.commands[key] = folder
        commands_signal.commands_updated.emit()
        self.assistant.show_notification_message(message=f"Команда '{key}' добавлена!")
        self.key_input.clear()
        self.folder_path.clear()
        self.error_label_clear()

    def show_error(self, message):
        """Показывает сообщение об ошибке."""
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def error_label_clear(self):
        self.error_label.setText("")
        self.error_label.setVisible(False)


class CommandsWidget(QWidget):
    """Класс для обработки окна 'Добавленные команды'"""

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.init_ui()
        self.update_commands_list()
        commands_signal.commands_updated.connect(self.update_commands_list)

    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.title = QLabel("Добавленные команды")

        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("background: transparent; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.title)

        self.commands_list = QListWidget(self)
        self.commands_list.setFont(QFont("Tahoma"))
        self.commands_list.setStyleSheet("border: none; font-size: 15px;")
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

        if not isinstance(self.assistant.commands, dict):
            debug_logger.error("Команды должны быть словарем")
            self.assistant.show_message("Некорректный формат команд", "Ошибка", "error")
            return

        for key, value in self.assistant.commands.items():
            item_text = f"{key} : {value}"
            item = QListWidgetItem(item_text)
            self.commands_list.addItem(item)

        self.select_last_item()

    def delete_command(self):
        """Удаление выбранной команды"""
        selected_items = self.commands_list.selectedItems()
        if not selected_items:
            self.assistant.show_message("Выберите команду для удаления", "Предупреждение", "warning")
            return

        # Удаляем выбранные команды
        for item in selected_items:
            key = item.text().split(" : ")[0]
            if key in self.assistant.commands:
                self.remove_command_from_process_names(self.assistant.commands[key])
                del self.assistant.commands[key]
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
            debug_logger.error(f"Ошибка при обновлении process_names.json: {e}")

    def save_commands(self):
        """Cохраняет команды"""
        try:
            with open(get_path('user_settings', 'commands.json'), 'w', encoding='utf-8') as file:
                json.dump(self.assistant.commands, file, ensure_ascii=False, indent=4)

        except Exception as e:
            debug_logger.error(f"Ошибка сохранения команд в CommandsWidget: {e}")


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
        main_layout.setSpacing(10)

        # Заголовок
        self.title = QLabel("Процессы ярлыков\n(нужны для закрытия)")

        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("background: transparent; font-size: 16px; font-weight: bold;")
        main_layout.addWidget(self.title)

        # Горизонтальный макет для левой и правой колонок
        content_layout = QHBoxLayout()

        # Левая колонка: список ярлыков
        left_layout = QVBoxLayout()
        self.links_label = QLabel("Ярлыки")
        self.links_label.setStyleSheet("background: transparent;")
        left_layout.addWidget(self.links_label)
        self.links_list = QListWidget()
        self.links_list.setStyleSheet("background: transparent;")
        self.links_list.itemClicked.connect(self.on_link_selected)
        left_layout.addWidget(self.links_list)

        # Правая колонка: список процессов
        right_layout = QVBoxLayout()
        self.processes_label = QLabel("Список процессов")
        self.processes_label.setStyleSheet("background: transparent;")
        right_layout.addWidget(self.processes_label)

        self.processes_list = QListWidget()
        self.processes_list.setStyleSheet("background: transparent;")
        right_layout.addWidget(self.processes_list)

        # Кнопки для управления процессами
        self.add_process_button = QPushButton("Добавить процесс")
        self.add_process_button.clicked.connect(self.add_process)
        right_layout.addWidget(self.add_process_button)

        self.remove_process_button = QPushButton("Удалить процесс")
        self.remove_process_button.clicked.connect(self.remove_process)
        right_layout.addWidget(self.remove_process_button)

        # Добавляем левую и правую части в горизонтальный макет
        content_layout.addLayout(left_layout, 2)
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

