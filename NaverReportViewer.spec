# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Naver Report Viewer (Windows build).

Usage (Windows):
    pip install pyinstaller
    pyinstaller NaverReportViewer.spec
Output:
    dist/NaverReportViewer.exe  (single-file, windowed)
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = []
hiddenimports += collect_submodules('fitz')  # PyMuPDF
hiddenimports += collect_submodules('PIL')
hiddenimports += ['lxml', 'lxml.etree', 'lxml._elementpath']

datas = []
datas += collect_data_files('fitz')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tests', 'test'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NaverReportViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed app (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
