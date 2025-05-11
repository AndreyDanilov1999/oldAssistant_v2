
from typing import Optional, Dict
import pygame
from logging_config import logger, debug_logger
import json
from pathlib import Path
from vgamepad import VX360Gamepad
from path_builder import get_path
import vgamepad as vg
import inputs
import time
import threading


class GamepadManager:
    def __init__(self, config_path=get_path("user_settings", "game_profiles_binds.json")):
        self.gamepad = vg.VX360Gamepad()  # Виртуальный Xbox контроллер
        self.running = False
        self.config = self._load_config(config_path)
        self.current_game = None
        self.active_holds = set()
        self.init_success = False
        try:
            self.gamepad = vg.VX360Gamepad()
            self.running = False
            self.config = self._load_config(config_path)
            self.current_game = None
            self.active_holds = set()
            self.last_x = 0.0
            self.last_y = 0.0
            self.last_rx = 0.0
            self.last_ry = 0.0
            self.hat_x = 0
            self.hat_y = 0

            self.init_success = True
        except Exception as e:
            print(f"[ERROR] Не удалось создать виртуальный геймпад: {e}")
            self.init_success = False

        # Кнопки геймпада
        self.button_map = {
            "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            "LB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            "RB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            "BACK": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            "LSTICK": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            "RSTICK": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB
        }

        # Сопоставление кнопок реального джойстика → команды
        self.inputs_to_command = {
            'BTN_SOUTH': 'A',
            'BTN_EAST': 'B',
            'BTN_NORTH': 'Y',
            'BTN_WEST': 'X',
            'BTN_TL': 'LB',
            'BTN_TR': 'RB',
            'BTN_SELECT': 'BACK',
            'BTN_START': 'START',
            'BTN_THUMBL': 'LSTICK',
            'BTN_THUMBR': 'RSTICK',
        }

        # Оси
        self.axis_map = {
            'ABS_X': self._scale_axis,
            'ABS_Y': self._scale_axis,
            'ABS_RX': self._scale_axis,
            'ABS_RY': self._scale_axis,
            'ABS_Z': lambda val: int((val / 255) * 255),  # LT
            'ABS_RZ': lambda val: int((val / 255) * 255),  # RT
        }

    def _load_config(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки конфига: {e}")
            return {"games": {}}

    def set_game(self, game_name: str) -> bool:
        if game_name in self.config.get("games", {}):
            self.current_game = game_name
            return True
        return False

    def trigger(self, command: str, hold: bool = False) -> bool:
        """Вызывается извне (например, от голосовых команд)"""
        if not self.current_game:
            self.set_game("God of War")  # по умолчанию

        game_config = self.config["games"][self.current_game]
        button_name = game_config.get(command.lower())

        if not button_name or button_name.upper() not in self.button_map:
            print(f"[ERROR] Не найдена кнопка для команды '{command}'")
            return False

        code = self.button_map[button_name.upper()]
        self.gamepad.press_button(code)
        self.gamepad.update()
        if hold:
            self.active_holds.add(code)
        else:
            def release_later():
                time.sleep(0.2)
                self.gamepad.release_button(code)
                self.gamepad.update()
            threading.Thread(target=release_later, daemon=True).start()
        return True

    def release(self, command: str) -> bool:
        if not self.current_game:
            return False

        game_config = self.config["games"][self.current_game]
        button_name = game_config.get(command.lower())

        if not button_name or button_name.upper() not in self.button_map:
            return False

        code = self.button_map[button_name.upper()]
        self.gamepad.release_button(code)
        self.gamepad.update()
        self.active_holds.discard(code)
        return True

    def start_proxy(self):
        """Запуск проксирования нажатий с реального на виртуальный геймпад"""
        if self.running:
            return

        self.running = True
        proxy_thread = threading.Thread(target=self._proxy_loop, daemon=True)
        proxy_thread.start()

    def stop_proxy(self):
        """Остановка проксирования"""
        self.running = False

    def _proxy_loop(self):
        """Основной цикл: читаем реальный геймпад и отправляем в виртуальный"""
        print("Запущено проксирование геймпада...")
        while self.running:
            try:
                events = inputs.get_gamepad()
                for event in events:
                    if event.ev_type == 'Key':
                        btn = self.inputs_to_command.get(event.code)
                        if btn:
                            if event.state:
                                self.gamepad.press_button(self.button_map[btn])
                            else:
                                self.gamepad.release_button(self.button_map[btn])
                            self.gamepad.update()

                    elif event.ev_type == 'Absolute':
                        self.handle_axis(event.code, event.state)

            except Exception as e:
                logger.error(f"Ошибка чтения геймпада: {e}")
                time.sleep(1)  # На случай частых ошибок

    def handle_button(self, btn_name, pressed):
        if btn_name.upper() not in self.button_map:
            return

        code = self.button_map[btn_name.upper()]
        if pressed:
            self.gamepad.press_button(code)
        else:
            self.gamepad.release_button(code)
        self.gamepad.update()

    def handle_axis(self, axis_name, value):
        try:
            if axis_name in ['ABS_X', 'ABS_Y', 'ABS_RX', 'ABS_RY']:
                # Обновляем значения
                if axis_name == 'ABS_X':
                    self.last_x = value / 32767.0  # [-1.0 ... 1.0]
                elif axis_name == 'ABS_Y':
                    self.last_y = value / 32767.0
                elif axis_name == 'ABS_RX':
                    self.last_rx = value / 32767.0
                elif axis_name == 'ABS_RY':
                    self.last_ry = value / 32767.0

                # Отправляем обновление стиков
                self.gamepad.left_joystick_float(x_value_float=self.last_x, y_value_float=self.last_y)
                self.gamepad.right_joystick_float(x_value_float=self.last_rx, y_value_float=self.last_ry)

            elif axis_name == 'ABS_Z':  # LT
                trigger_val = max(0.0, min(1.0, value / 255.0))
                self.gamepad.left_trigger_float(value_float=trigger_val)

            elif axis_name == 'ABS_RZ':  # RT
                trigger_val = max(0.0, min(1.0, value / 255.0))
                self.gamepad.right_trigger_float(value_float=trigger_val)

            elif axis_name == 'ABS_HAT0X':
                self.handle_pov('x', value)

            elif axis_name == 'ABS_HAT0Y':
                self.handle_pov('y', value)

            else:
                return

            # Одно обновление на событие (оптимально)
            self.gamepad.update()

        except Exception as e:
            logger.error(f"[ERROR] Не удалось обработать ось {axis_name}: {e}")

    def handle_pov(self, axis, value):
        dpad_map = {
            (-1, 0): vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
            (1, 0): vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
            (0, -1): vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
            (0, 1): vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
        }

        if not hasattr(self, '_dpad_state'):
            self._dpad_state = set()

        # Обновляем состояние осей
        if axis == 'x':
            self.hat_x = value
        elif axis == 'y':
            self.hat_y = value

        x = self.hat_x
        y = self.hat_y

        # Определяем активные направления
        active = set()
        if y == 1:
            active.add(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
        elif y == -1:
            active.add(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
        if x == -1:
            active.add(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
        elif x == 1:
            active.add(vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)

        # Нажимаем новые кнопки
        for btn in active - self._dpad_state:
            self.gamepad.press_button(btn)

        # Отпускаем неактивные
        for btn in self._dpad_state - active:
            self.gamepad.release_button(btn)

        self._dpad_state = active
        self.gamepad.update()

    @staticmethod
    def _scale_axis(value):
        """Масштабирует ось с [-32768..32767] на [0..32767]"""
        return int(((value + 32768) // 2) * 32767 / 32767)

    def cleanup(self):
        """Сброс всех активных действий"""
        for code in list(self.active_holds):
            self.gamepad.release_button(code)
        self.gamepad.reset()
        self.gamepad.update()
        self.active_holds.clear()

    def find_command(self, phrase: str) -> Optional[str]:
        """Поиск голосовой команды в фразе"""
        if not self.current_game:
            return None

        # Получаем список доступных команд для текущей игры
        game_commands = self.config.get("games", {}).get(self.current_game, {})

        # Проверяем каждую команду на вхождение в фразу
        for cmd in game_commands:
            if cmd.lower() in phrase.lower():
                return cmd  # Возвращаем точное название команды из конфига

        return None  # Ничего не найдено
