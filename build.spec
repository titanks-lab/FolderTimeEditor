# -*- mode: python ; coding: utf-8 -*-
"""
FolderTimeEditor PyInstaller 打包配置
===============================
打包命令: pyinstaller build.spec
输出: dist/FolderTimeEditor.exe (单文件绿色版)

系统要求:
  - Windows 7+
  - Python 3.8+
  - 依赖: pip install -r requirements.txt

打包流程:
  1. 安装依赖: pip install -r requirements.txt
  2. 构建: pyinstaller build.spec
  3. 输出位于 dist/FolderTimeEditor.exe
"""

import os
import sys
import shutil

# ── 项目根路径 ──────────────────────────────────────
_SPEC_FILE = os.environ.get('PYINSTALLER_SPEC_FILE', '')
if _SPEC_FILE:
    # PyInstaller 7+ passes the spec path via env
    ROOT_DIR = os.path.dirname(os.path.abspath(_SPEC_FILE))
elif '__file__' in dir():
    # Local execution: __file__ is defined
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    # Fallback: assume CWD is project root (standard pyinstaller invocation)
    ROOT_DIR = os.path.abspath('.')

# ── 检测 UPX 是否可用 ──────────────────────────────
_has_upx = False
_upx_path = shutil.which("upx")
if _upx_path:
    _has_upx = True
elif os.path.isfile(r"C:\tools\upx\upx.exe"):
    _has_upx = True
    _upx_path = r"C:\tools\upx\upx.exe"
elif os.path.isfile(r"C:\Program Files\upx\upx.exe"):
    _has_upx = True
    _upx_path = r"C:\Program Files\upx\upx.exe"

# ── 版本信息文件（预生成于 repo 中） ─────────────
_version_info_path = os.path.join(ROOT_DIR, "file_version_info.txt")
if not os.path.isfile(_version_info_path):
    print("[WARN] Version info file not found: file_version_info.txt")
    print("[WARN] EXE will have no version metadata")
    _version_info_path = None

# ── EXE 图标路径 ──────────────────────────────────
_icon_path = os.path.join(ROOT_DIR, "assets", "icon.ico")
if not os.path.isfile(_icon_path):
    print(f"[WARN] 图标文件不存在: {_icon_path}")
    print("[WARN] 打包将使用默认图标")
    _icon_path = None

# ═══════════════════════════════════════════════════
# PyInstaller 构建块
# ═══════════════════════════════════════════════════

a = Analysis(
    # ── 入口脚本 ───────────────────────────────────
    [os.path.join(ROOT_DIR, "main.py")],

    pathex=[ROOT_DIR],

    binaries=[],

    datas=[
        # 打包 assets 目录（图标、配置文件等）
        (os.path.join(ROOT_DIR, "assets"), "assets"),
    ],

    hiddenimports=[
        # 项目内部模块
        "core",
        "core.timestamp_handler",
        "gui",
        "gui.widgets",
        "gui.dialogs",
        # ttkbootstrap 核心及子模块
        "ttkbootstrap",
        "ttkbootstrap.constants",
        "ttkbootstrap.widgets",
        "ttkbootstrap.dialogs",
        "ttkbootstrap.toast",
        "ttkbootstrap.tableview",
        "ttkbootstrap.scrolled",
        "ttkbootstrap.style",
        "ttkbootstrap.themes",
        "ttkbootstrap.icons",
        "ttkbootstrap.tooltip",
        "ttkbootstrap.meters",
        "ttkbootstrap.progressbar",
        "ttkbootstrap.floodgauge",
        "ttkbootstrap.widgets.calendar",
        "ttkbootstrap.widgets.datepicker",
        "ttkbootstrap.widgets.meter",
        "ttkbootstrap.widgets.progressbar",
        # tkinter 标准模块
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.ttk",
        "tkinter.colorchooser",
        "tkinter.font",
        "tkinter.simpledialog",
        # Python 标准库（项目实际使用的）
        "calendar",
        "datetime",
        "dataclasses",
        "fnmatch",
        "json",
        "os",
        "pathlib",
        "shutil",
        "sys",
        "threading",
        "time",
        "typing",
        "queue",
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    excludes=[
        # ── 显式排除的大体积无用模块（减小 exe 体积） ──
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "sklearn",
        "tensorflow",
        "torch",
        "keras",
        "cv2",
        "PIL.ImageShow",
        "PIL.ImageQt",
        "PIL.ImageGrab",
        "notebook",
        "jupyter",
        "IPython",
        "bokeh",
        "plotly",
        "dash",
        "flask",
        "django",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",
        "cairo",
        "gi",
        "gtk",
        "cryptography",
        "asyncio",
        "unittest",
        "pytest",
        "sphinx",
        "docutils",
        "setuptools",
        "pip",
        "wheel",
        "tornado",
        "selenium",
        "requests",
        "urllib3",
        "bs4",
        "lxml",
        "yaml",
        "toml",
        "socks",
        "charset_normalizer",
        "idna",
        "certifi",
        "markupsafe",
        "jinja2",
        "werkzeug",
        "click",
    ],

    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    # ── 输出名称 ──────────────────────────────────
    name="FolderTimeEditor",
    debug=False,
    strip=False,
    upx=_has_upx,
    upx_exclude=[],
    runtime_tmpdir=None,
    # ── 窗口模式（隐藏控制台） ─────────────────────
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # ── 版本信息 ──────────────────────────────────
    version=_version_info_path if _version_info_path and os.path.exists(_version_info_path) else None,
    # ── 图标 ──────────────────────────────────────
    icon=_icon_path,
)

print("=" * 60)
print(f"[OK] Build config loaded")
print(f"[INFO] Entry: main.py")
print(f"[INFO] Output: dist/FolderTimeEditor.exe")
print(f"[INFO] Mode: single file / windowed (no console)")
print(f"[INFO] UPX: {'enabled' if _has_upx else 'not found, skip'}")
print(f"[INFO] Version: {'1.0.0.0' if _version_info_path and os.path.exists(_version_info_path) else 'none'}")
print(f"[INFO] Icon: {os.path.basename(_icon_path) if _icon_path else 'default'}")
print("=" * 60)
