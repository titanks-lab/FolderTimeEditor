#!/usr/bin/env python3
"""FolderTimeEditor - 文件夹时间批量修改工具

Windows 平台批量修改文件夹/文件时间属性的桌面工具。
使用 tkinter + ttkbootstrap 构建现代化 Windows 原生界面。

Usage:
    python main.py
"""
from __future__ import annotations

import sys
import os

# Ensure the project root is on the path
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def main():
    """Application entry point."""
    # Platform check (soft warning only — core can still be developed on Linux)
    if sys.platform != 'win32':
        print(f'[提示] 此工具主要面向 Windows 平台。当前系统: {sys.platform}')

    try:
        from gui.app import FolderTimeEditor
        app = FolderTimeEditor()
        app.mainloop()
    except ImportError as e:
        print(f'[错误] 导入失败: {e}')
        print('请确保已安装依赖: pip install ttkbootstrap tkinterdnd2')
        sys.exit(1)
    except Exception as e:
        print(f'[错误] 启动失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
