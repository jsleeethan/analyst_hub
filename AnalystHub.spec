# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_all

# venv가 miniconda 환경(paper_study)을 base로 사용하므로 conda의 Library/bin DLL을 명시적으로 포함
CONDA_BASE = sys.base_prefix  # 보통: C:\Users\USER\miniconda3\envs\paper_study
CONDA_LIB_BIN = os.path.join(CONDA_BASE, 'Library', 'bin')
CONDA_LIB = os.path.join(CONDA_BASE, 'Library', 'lib')

tk_datas, tk_binaries, tk_hiddenimports = collect_all('tkinter')
fitz_datas, fitz_binaries, fitz_hiddenimports = collect_all('pymupdf')

# Tcl/Tk DLL을 EXE 루트에 직접 포함 (_tkinter.pyd가 import 시 같은 폴더에서 로드)
extra_binaries = []
for dll_name in ('tcl86t.dll', 'tk86t.dll', 'zlib1.dll'):
    dll_path = os.path.join(CONDA_LIB_BIN, dll_name)
    if os.path.exists(dll_path):
        extra_binaries.append((dll_path, '.'))

# Tcl/Tk 스크립트 라이브러리 폴더 (_tkinter 초기화 시 필요)
extra_datas = []
for lib_name in ('tcl8.6', 'tk8.6', 'tcl8'):
    lib_path = os.path.join(CONDA_LIB, lib_name)
    if os.path.exists(lib_path):
        extra_datas.append((lib_path, os.path.join('lib', lib_name)))

a = Analysis(
    ['main.py'],
    pathex=[CONDA_LIB_BIN],
    binaries=tk_binaries + fitz_binaries + extra_binaries,
    datas=tk_datas + fitz_datas + extra_datas,
    hiddenimports=tk_hiddenimports + fitz_hiddenimports + ['_tkinter'],
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
    a.binaries,
    a.datas,
    [],
    name='AnalystHub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
