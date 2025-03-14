import json
import os

def update_settings(settings_file="settings.json", default_settings=None):
    """
    Проверяет файл настроек на наличие ключей из default_settings.
    Если ключ отсутствует, добавляет его со значением по умолчанию.
    """
    if default_settings is None:
        default_settings = {
            "voice": "johnny",
            "assistant_name": "джо",
            "assist_name2": "джо",
            "assist_name3": "джо",
            "steam_path": "D:/Steam/steam.exe",
            "is_censored": True,
            "volume_assist": 0.2,
            "show_upd_msg": False  # Значение по умолчанию
        }

    # Загружаем текущие настройки
    if os.path.exists(settings_file):
        with open(settings_file, "r", encoding="utf-8") as file:
            try:
                settings = json.load(file)
            except json.JSONDecodeError:
                settings = {}
    else:
        settings = {}

    # Обновляем настройки, если ключи отсутствуют
    updated = False
    for key, value in default_settings.items():
        if key not in settings:
            settings[key] = value
            updated = True

    # Сохраняем обновленные настройки, если они изменились
    if updated:
        with open(settings_file, "w", encoding="utf-8") as file:
            json.dump(settings, file, ensure_ascii=False, indent=4)

    return settings


# Пример использования
settings = update_settings()
print(settings)