# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_assistant.py'],
    pathex=['G:/PycharmProjects/OldAssistant'],
    binaries=[(r'G:/PycharmProjects/OldAssistant/venv/Lib/site-packages/vosk/libvosk.dll', 'vosk')],
    datas=[
        ('G:/PycharmProjects/OldAssistant/assist-min.ico', '.'),
        ('G:/PycharmProjects/OldAssistant/settings.json', '.'),
        ('G:/PycharmProjects/OldAssistant/process_names.json', '.'),
        ('G:/PycharmProjects/OldAssistant/commands.json', '.'),
        ('G:/PycharmProjects/OldAssistant/assistant.log', '.'),
        ('G:/PycharmProjects/OldAssistant/function_list.py', '.'),
        ('G:/PycharmProjects/OldAssistant/function_list_main.py', '.'),
        ('G:/PycharmProjects/OldAssistant/lists.py', '.'),
        ('G:/PycharmProjects/OldAssistant/logging_config.py', '.'),
        ('G:/PycharmProjects/OldAssistant/run_script.py', '.'),
        ('G:/PycharmProjects/OldAssistant/script_audio.py', '.'),
        ('G:/PycharmProjects/OldAssistant/speak_functions.py', '.'),
        ('G:/PycharmProjects/OldAssistant/add_program_func.py', '.'),
        ('G:/PycharmProjects/OldAssistant/start_assistant.bat', '.'),
        ('G:/PycharmProjects/OldAssistant/speak_voice', 'speak_voice'),
        ('G:/PycharmProjects/OldAssistant/model_ru', 'model_ru'),
        ('G:/PycharmProjects/OldAssistant/links for assist', 'links for assist'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assist-min.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Assistant',
)
