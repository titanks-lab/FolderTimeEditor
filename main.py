#!/usr/bin/env python3
"""FolderTimeEditor - 文件夹时间批量修改工具

Windows 平台批量修改文件夹/文件时间属性的桌面工具。
使用 tkinter + ttkbootstrap 构建现代化 Windows 原生界面。

Usage:
    python main.py              # 源码运行
    FolderTimeEditor.exe        # 打包版运行
"""
from __future__ import annotations

import sys
import os
import traceback
import tempfile
from datetime import datetime


_ERROR_LOG = os.path.join(
    tempfile.gettempdir(),
    f'FolderTimeEditor_error_{datetime.now():%Y%m%d_%H%M%S}.log'
)


def _write_error_log(exc_info=None):
    """Write detailed error information to a log file."""
    try:
        with open(_ERROR_LOG, 'w', encoding='utf-8') as f:
            f.write(f'FolderTimeEditor Crash Report\n')
            f.write(f'Time: {datetime.now():%Y-%m-%d %H:%M:%S}\n')
            f.write(f'Platform: {sys.platform}\n')
            f.write(f'Python: {sys.version}\n')
            f.write(f'Executable: {sys.executable}\n')
            f.write(f'Args: {sys.argv}\n')
            f.write(f'CWD: {os.getcwd()}\n\n')

            if exc_info:
                f.write('Traceback:\n')
                traceback.print_exception(*exc_info, file=f)

            f.write('\n\nEnvironment:\n')
            for key, val in sorted(os.environ.items()):
                if not any(s in key.lower() for s in ('token', 'secret', 'password', 'key', 'auth')):
                    f.write(f'  {key}={val}\n')

        return _ERROR_LOG
    except Exception:
        # Can't even write the log file
        return None


def _show_error_dialog(message: str, log_path: str = None):
    """Show a native Windows error dialog via ctypes, or fall back to print."""
    full_msg = message
    if log_path:
        full_msg += f'\n\n错误详情已保存至:\n{log_path}'

    try:
        # Try Windows native MessageBox
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            full_msg,
            'FolderTimeEditor - 启动错误',
            0x10 | 0x1000  # MB_ICONERROR | MB_SYSTEMMODAL
        )
    except Exception:
        # Fallback: print to stderr (visible if run from cmd)
        print(f'[FATAL] {full_msg}', file=sys.stderr)
        # Also try tkinter messagebox if available
        try:
            import tkinter
            from tkinter import messagebox
            root = tkinter.Tk()
            root.withdraw()
            messagebox.showerror(
                'FolderTimeEditor - 启动错误',
                full_msg
            )
            root.destroy()
        except Exception:
            pass


def _is_frozen():
    """Check if running as a PyInstaller-frozen executable."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def main():
    """Application entry point."""
    exc_info = None
    log_path = None

    try:
        # ── Show splash for instant user feedback ──
        _splash = None
        try:
            import tkinter as _tk
            _splash = _tk.Tk()
            _splash.title('')
            _splash.overrideredirect(True)
            _splash.geometry('300x80+{}+{}'.format(
                (_splash.winfo_screenwidth() - 300) // 2,
                (_splash.winfo_screenheight() - 80) // 2
            ))
            _splash.configure(bg='#1a1a2e')
            _tk.Label(
                _splash, text='FolderTimeEditor', fg='#e94560',
                bg='#1a1a2e', font=('Segoe UI', 14, 'bold')
            ).pack(pady=(12, 0))
            _tk.Label(
                _splash, text='正在加载...', fg='#aaaaaa',
                bg='#1a1a2e', font=('Segoe UI', 10)
            ).pack()
            _splash.update()
        except Exception:
            _splash = None

        # Ensure the project root is on the path (for source runs)
        if not _is_frozen():
            _project_root = os.path.dirname(os.path.abspath(__file__))
            if _project_root not in sys.path:
                sys.path.insert(0, _project_root)

        # Import and launch the app
        from gui.app import FolderTimeEditor
        app = FolderTimeEditor()

        # Close splash when main window is ready
        if _splash:
            _splash.destroy()
            _splash = None

        app.mainloop()

    except ImportError as e:
        exc_info = sys.exc_info()
        log_path = _write_error_log(exc_info)
        msg = f'导入失败: {e}\n请确保已安装依赖: pip install -r requirements.txt'
        _show_error_dialog(msg, log_path)
        sys.exit(1)

    except Exception as e:
        exc_info = sys.exc_info()
        log_path = _write_error_log(exc_info)
        msg = f'程序启动失败: {e}'
        _show_error_dialog(msg, log_path)
        sys.exit(1)


if __name__ == '__main__':
    main()
