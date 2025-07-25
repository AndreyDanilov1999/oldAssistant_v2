# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Главные файлы проекта
main_script = 'swap_updater_app/swap_updater.py'
additional_files = [
    ('G:/PycharmProjects/oldAssistant_v2/swap_updater_app/swap.ico', '.'),
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
    name='swap-updater',      # Имя выходного файла
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,              # Сжатие исполняемого файла
    console=False,          # True - показывать консоль, False - скрыть
    icon='G:/PycharmProjects/oldAssistant_v2/swap_updater_app/swap.ico'
)