# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller спецификация для сборки Docker Simple Manager."""

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules  # type: ignore

block_cipher = None

PROJECT_ROOT = Path.cwd()
SRC_ROOT = PROJECT_ROOT / "src"

datas = []
datas += collect_data_files("src.i18n", includes=["strings/*.json"])
datas += collect_data_files("src.ui.styles", includes=["*.qss"])
datas += collect_data_files(
    "src.ui.resources",
    includes=["icons/*", "images/*", "fonts/*"],
)

BINARY_NAME = os.environ.get("DSM_BINARY_NAME", "dsm")
DIST_NAME = os.environ.get("DSM_DIST_NAME", "dsm-linux")

hiddenimports = collect_submodules("src.i18n") + collect_submodules("src.ui")

a = Analysis(
    ["src/main.py"],
    pathex=[str(SRC_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests", "docs", "tmp"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=BINARY_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=DIST_NAME,
)
