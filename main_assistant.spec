# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_assistant.py'],
    pathex=['G:/PycharmProjects/oldAssistant_v2'],
    binaries=[(r'G:\PycharmProjects\oldAssistant_v2\venv_1\Lib\site-packages\vosk\libvosk.dll', 'vosk')],
    datas=[
        ('G:/PycharmProjects/oldAssistant_v2/assist-min.ico', '.'),
        ('G:/PycharmProjects/oldAssistant_v2/user_settings/settings.json', 'user_settings'),
        ('G:/PycharmProjects/oldAssistant_v2/user_settings/process_names.json', 'user_settings'),
        ('G:/PycharmProjects/oldAssistant_v2/user_settings/color_settings.json', 'user_settings'),
        ('G:/PycharmProjects/oldAssistant_v2/user_settings/commands.json', 'user_settings'),
        ('G:/PycharmProjects/oldAssistant_v2/user_settings/links.json', 'user_settings'),
        ('G:/PycharmProjects/oldAssistant_v2/func_list.py', '.'),
        ('G:/PycharmProjects/oldAssistant_v2/function_list_main.py', '.'),
        ('G:/PycharmProjects/oldAssistant_v2/lists.py', '.'),
        ('G:/PycharmProjects/oldAssistant_v2/logging_config.py', '.'),
        ('G:/PycharmProjects/oldAssistant_v2/run_script.py', '.'),
        ('G:/PycharmProjects/oldAssistant_v2/script_audio.py', '.'),
        ('G:/PycharmProjects/oldAssistant_v2/speak_functions.py', '.'),
        ('G:/PycharmProjects/oldAssistant_v2/speak_voice', 'speak_voice'),
        ('G:/PycharmProjects/oldAssistant_v2/model_ru', 'model_ru'),
        ('G:/PycharmProjects/oldAssistant_v2/user_settings/links for assist', 'user_settings/links for assist'),
        ('G:/PycharmProjects/oldAssistant_v2/user_settings/presets', 'user_settings/presets'),
    ],
    hiddenimports=['vosk', 'pyaudio', 'func_list'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
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
