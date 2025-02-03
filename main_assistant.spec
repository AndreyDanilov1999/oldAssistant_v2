# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_assistant.py'],
    pathex=['D:\My Files\OldAssistant_v2'],
    binaries=[(r'D:\My Files\OldAssistant_v2/venv/Lib/site-packages/vosk/libvosk.dll', 'vosk')],
    datas=[
        ('D:\My Files\OldAssistant_v2/assist-min.ico', '.'),
        ('D:\My Files\OldAssistant_v2/settings.json', '.'),
        ('D:\My Files\OldAssistant_v2/process_names.json', '.'),
        ('D:\My Files\OldAssistant_v2/commands.json', '.'),
        ('D:\My Files\OldAssistant_v2/links.json', '.'),
        ('D:\My Files\OldAssistant_v2/func_list.py', '.'),
        ('D:\My Files\OldAssistant_v2/function_list_main.py', '.'),
        ('D:\My Files\OldAssistant_v2/lists.py', '.'),
        ('D:\My Files\OldAssistant_v2/logging_config.py', '.'),
        ('D:\My Files\OldAssistant_v2/run_script.py', '.'),
        ('D:\My Files\OldAssistant_v2/script_audio.py', '.'),
        ('D:\My Files\OldAssistant_v2/speak_functions.py', '.'),
        ('D:\My Files\OldAssistant_v2/speak_voice', 'speak_voice'),
        ('D:\My Files\OldAssistant_v2/model_ru', 'model_ru'),
        ('D:\My Files\OldAssistant_v2/links for assist', 'links for assist'),
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
