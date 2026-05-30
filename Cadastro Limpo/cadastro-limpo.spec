# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('D:\\cadastro-limpo\\Cadastro Limpo\\desktop_ui\\icon.ico', 'desktop_ui'), ('D:\\cadastro-limpo\\Cadastro Limpo\\desktop_ui\\icon.png', 'desktop_ui'), ('D:\\cadastro-limpo\\Cadastro Limpo\\patterns.json', '.')]
datas += collect_data_files('sanitiser')


a = Analysis(
    ['desktop_ui\\main.py'],
    pathex=['D:\\cadastro-limpo\\Cadastro Limpo'],
    binaries=[],
    datas=datas,
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
    name='cadastro-limpo',
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
    icon=['D:\\cadastro-limpo\\Cadastro Limpo\\desktop_ui\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cadastro-limpo',
)
