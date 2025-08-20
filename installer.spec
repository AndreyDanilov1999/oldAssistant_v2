# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Главные файлы проекта (сборка в один файл)
main_script = 'install_app/installer.py'
additional_files = [
    ('G:/PycharmProjects/oldAssistant_v2/install_app/color.json', '.'),
    ('G:/PycharmProjects/oldAssistant_v2/install_app/logo.svg', '.'),
    ('G:/PycharmProjects/oldAssistant_v2/install_app/icon.ico', '.'),
    ('G:/PycharmProjects/oldAssistant_v2/install_app/Update.exe', '.'),
    ('G:/PycharmProjects/oldAssistant_v2/install_app/utils.py', '.'),
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
    name='Setup',      # Имя выходного файла
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,              # Сжатие исполняемого файла
    console=False,          # True - показывать консоль, False - скрыть
    uac_admin=True,
    icon='G:/PycharmProjects/oldAssistant_v2/install_app/icon.ico'
)