import json
import os

from add_program_func import get_base_directory, get_target_path, fix_path, get_process_name, read_url_shortcut


def handler_links(filename, action):
    """
    Обработчик ярлыков в зависимости от их расширения
    """
    root_folder = os.path.join(get_base_directory(), "links for assist")
    print(filename)
    # Получаем путь к ярлыку
    shortcut_path = os.path.join(root_folder, filename)
    print(shortcut_path)

    # Обработка .lnk файлов
    if filename.endswith(".lnk"):
        try:
            target_path, arguments = get_target_path(shortcut_path)
            # Исправляем пути
            target_path = fix_path(target_path)
            shortcut_path = fix_path(shortcut_path)
            # Извлекаем имя процесса
            process_name = get_process_name(target_path)
        except Exception as e:
            print(f"Ошибка при извлечении пути из ярлыка {filename}: {e}")

        if action == 'open':
            print('open')
        if action == 'close':
            print('close')

    # Обработка .url файлов (Steam-игры)
    if filename.endswith(".url"):
        try:
            game_id = read_url_shortcut(shortcut_path)
            print(game_id)
            if not game_id:
                print(f"Не удалось извлечь game_id из файла {filename}")
        except Exception as e:
            print(f"Ошибка при чтении .url файла {filename}: {e}")

        if action == 'open':
            print('open_url')
        if action == 'close':
            print('close')


def handle_app_command(text, action):
    """Обработка команд для приложений"""
    for keyword, filename in commands.items():
        if keyword in text:
            # Здесь filename — это название ярлыка с расширением
            handler_links(filename, action)  # Вызываем обработчик ярлыков
            return True  # Возвращаем True, если команда была успешно обработана
    return False  # Возвращаем False, если команда не была найдена

def load_commands(filename):
    """Загружает команды из JSON-файла."""
    file_path = os.path.join(get_base_directory(), filename)  # Полный путь к файлу
    try:
        if not os.path.exists(file_path):
            print(f"Файл {file_path} не найден.")
            return {}  # Возвращаем пустой словарь, если файл не найден

        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()  # Читаем содержимое и убираем пробелы
            if not content:  # Если файл пустой
                return {}  # Возвращаем пустой словарь
            return json.loads(content)  # Загружаем JSON
    except json.JSONDecodeError:
        print(f"Ошибка: файл {file_path} содержит некорректный JSON.")
        return {}  # Возвращаем пустой словарь при ошибке декодирования
    except Exception as e:
        print(f"Ошибка при загрузке команд из файла {file_path}: {e}")
        return {}  # Возвращаем пустой словарь при других ошибках

commands = load_commands(os.path.join(get_base_directory(), 'commands.json'))
text = "парсек"
# print(handle_app_command(text, action='open'))
handle_app_command(text, action='close')

class AppCommandWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.base_path = get_base_directory()
        self.commands = self.load_commands(os.path.join(self.base_path, 'commands.json'))
        self.load_functions()  # Загружаем функции при инициализации

        # Устанавливаем фиксированный размер окна
        self.setFixedSize(400, 350)
        self.setStyleSheet("""
                    QDialog {
                        background-color: #2E3440;
                        color: #88C0D0;
                    }
                    QLabel {
                        color: #88C0D0;
                    }
                    QLineEdit {
                        background-color: #2E3450;
                        color: #88C0D0;
                    }
                    QPushButton {
                        background-color: #2E3450;
                        color: #88C0D0;
                    }
                    QComboBox {
                        background-color: #2E3450;
                        border: 1px solid;
                        border-radius: 4px;
                        color: #88C0D0;
                        font-size: 12px;
                        padding: 5px;
                    }
                """)
        # Установка иконки для окна
        self.setWindowIcon(QIcon(os.path.join(get_base_directory(), 'assist-min.ico')))

    def init_ui(self):
        self.setWindowTitle("Добавить команду")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Поле для ввода ключа
        self.key_input = QLineEdit(self)
        self.key_input.setPlaceholderText("Команда (ключ)")
        layout.addWidget(QLabel("Команда (ключ):"))
        layout.addWidget(self.key_input)

        # Поле для выбора функции открытия
        self.open_func_combo = QComboBox(self)
        layout.addWidget(QLabel("Функция открытия:"))
        layout.addWidget(self.open_func_combo)

        # Поле для выбора функции закрытия
        self.close_func_combo = QComboBox(self)
        layout.addWidget(QLabel("Функция закрытия:"))
        layout.addWidget(self.close_func_combo)

        # Поле для ввода имени функции для удаления
        self.delete_func_input = QLineEdit(self)
        self.delete_func_input.setPlaceholderText("Введите имя функции для удаления")
        layout.addWidget(QLabel("Имя функции для удаления:"))
        layout.addWidget(self.delete_func_input)

        # Кнопка удаления функции
        self.delete_func_button = QPushButton("Удалить функцию", self)
        self.delete_func_button.clicked.connect(self.delete_function_ui)
        layout.addWidget(self.delete_func_button)

        layout.addStretch()

        # Кнопка применения
        self.apply_button = QPushButton("Применить", self)
        self.apply_button.clicked.connect(self.apply_command)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def load_commands(self, filename):
        """Загружает команды из JSON-файла."""
        file_path = os.path.join(self.base_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.error(f"Файл {filename} не найден по пути: {file_path}")
            QMessageBox.critical(self, "Ошибка", f"Файл {filename} не найден.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Ошибка: файл {filename} содержит некорректный JSON.")
            QMessageBox.critical(self, "Ошибка", "Ошибка в формате файла JSON.")
            return {}

    def save_commands(self, filename):
        """Сохраняет команды в JSON-файл."""
        file_path = os.path.join(self.base_path, filename)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(self.commands, file, ensure_ascii=False, indent=4)
            logger.info("Команда обновлена в файле.")

    def get_functions_from_file(self, file_path):
        """
        Извлекает имена функций из файла Python.
        :param file_path: Путь к файлу.
        :return: Списки функций, начинающихся на 'open' и 'close'.
        """
        open_funcs = []
        close_funcs = []

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Регулярное выражение для поиска функций
            function_pattern = re.compile(r'^def\s+(open_\w+|close_\w+)\(', re.MULTILINE)

            # Ищем все функции
            matches = function_pattern.findall(content)
            for func_name in matches:
                if func_name.startswith('open'):
                    open_funcs.append(func_name)
                elif func_name.startswith('close'):
                    close_funcs.append(func_name)

        except Exception as e:
            logger.error(f"Ошибка при чтении файла {file_path}: {e}")

        return open_funcs, close_funcs

    def load_functions(self):
        """Загружает функции открытия и закрытия в комбобоксы."""
        file_path = os.path.join(self.base_path, 'function_list.py')
        self.open_funcs, self.close_funcs = self.get_functions_from_file(file_path)

        # Очищаем комбобоксы и добавляем функции
        self.open_func_combo.clear()
        self.close_func_combo.clear()
        self.open_func_combo.addItems(self.open_funcs)
        self.close_func_combo.addItems(self.close_funcs)

    def apply_command(self):
        """Добавляет новую команду в JSON-файл."""
        key = self.key_input.text()
        selected_open_func_name = self.open_func_combo.currentText()
        selected_close_func_name = self.close_func_combo.currentText()

        try:
            # Проверка на существование ключа
            if key in self.commands:
                QMessageBox.warning(self, "Предупреждение", f"Команда '{key}' уже существует.")
                return

            # Добавляем новую команду в словарь commands
            self.commands[key] = {
                "open": selected_open_func_name,
                "close": selected_close_func_name
            }
            # Сохраняем обновленный словарь в JSON-файл
            self.save_commands('commands.json')

            QMessageBox.information(self, "Успех",
                                    f"Команда '{key}' успешно добавлена.\nНеобходим перезапуск программы.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            logger.error(f"Ошибка: {e}")

    def delete_function_from_file(self, function_name, file_path):
        """
        Удаляет функцию из файла по её названию.
        :param function_name: Имя функции для удаления.
        :param file_path: Путь к файлу, из которого нужно удалить функцию.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Регулярное выражение для поиска начала функции
            function_pattern = re.compile(rf'^def {function_name}\(')

            new_lines = []
            skip = False  # Флаг для пропуска строк внутри функции

            for line in lines:
                if function_pattern.match(line):
                    skip = True  # Начало функции, пропускаем строки
                elif skip and line.startswith('def '):
                    skip = False  # Конец функции (началась новая функция)
                elif skip and line.strip() == '':
                    continue  # Пропускаем пустые строки внутри функции
                elif skip:
                    continue  # Пропускаем строки внутри функции

                if not skip:
                    new_lines.append(line)

            # Записываем обновленное содержимое обратно в файл
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(new_lines)

            logger.info(f"Функция '{function_name}' успешно удалена из файла.")
        except Exception as e:
            logger.error(f"Ошибка при удалении функции: {e}")

    def delete_function(self, function_name):
        """Удаляет функцию из файла function_list.py."""
        file_path = os.path.join(self.base_path, 'function_list.py')
        try:
            self.delete_function_from_file(function_name, file_path)
            QMessageBox.information(self, "Успех", f"Функция '{function_name}' успешно удалена.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении функции: {e}")

    def delete_function_ui(self):
        """Обработчик нажатия кнопки удаления функции."""
        function_name = self.delete_func_input.text()
        if function_name:
            self.delete_function(function_name)
        else:
            QMessageBox.warning(self, "Ошибка", "Введите имя функции для удаления.")