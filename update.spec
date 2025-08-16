# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Главные файлы проекта (сборка в один файл)
main_script = 'update_app/update.py'
additional_files = [
    ('G:/PycharmProjects/oldAssistant_v2/update_app/color.json', '.'),
    ('G:/PycharmProjects/oldAssistant_v2/update_app/logo.svg', '.'),
    ('G:/PycharmProjects/oldAssistant_v2/update_app/icon.ico', '.'),
]

a = Analysis(
    [main_script],
    pathex=[],
    binaries=[],
    datas=additional_files,
    hiddenimports=[
        'requests',
        'json',
        'os',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False  # Важно для onefile!
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Update',      # Имя выходного файла
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,              # Сжатие исполняемого файла
    console=False,          # True - показывать консоль, False - скрыть
    icon='G:/PycharmProjects/oldAssistant_v2/update_app/icon.ico'
)