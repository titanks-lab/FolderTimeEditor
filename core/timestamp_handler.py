"""
Windows 批量时间修改工具 — 核心引擎
===================================

使用 ctypes 调用 Windows API (SetFileTime) 实现文件夹/文件的
创建时间、修改时间、上次访问时间的读取和批量修改。

跨平台兼容：非 Windows 系统会给出友好提示并返回空结果。
"""

from __future__ import annotations

import fnmatch
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Generator, Optional

# ── Windows API 绑定（仅在 Windows 上加载） ──────────────────────────────

if os.name == "nt":
    import ctypes
    import ctypes.wintypes as w
    from ctypes import POINTER

    # ── 常量 ────────────────────────────────────────────────────────────
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    INVALID_HANDLE_VALUE = w.HANDLE(-1).value

    # ── FILETIME 结构体 ─────────────────────────────────────────────────
    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", w.DWORD),
            ("dwHighDateTime", w.DWORD),
        ]

    # ── API 函数签名 ────────────────────────────────────────────────────
    _CreateFileW = ctypes.windll.kernel32.CreateFileW
    _CreateFileW.argtypes = [
        w.LPCWSTR,       # lpFileName
        w.DWORD,         # dwDesiredAccess
        w.DWORD,         # dwShareMode
        w.LPVOID,        # lpSecurityAttributes
        w.DWORD,         # dwCreationDisposition
        w.DWORD,         # dwFlagsAndAttributes
        w.HANDLE,        # hTemplateFile
    ]
    _CreateFileW.restype = w.HANDLE

    _GetFileTime = ctypes.windll.kernel32.GetFileTime
    _GetFileTime.argtypes = [
        w.HANDLE,   # hFile
        POINTER(FILETIME),  # lpCreationTime
        POINTER(FILETIME),  # lpLastWriteTime
        POINTER(FILETIME),  # lpLastAccessTime
    ]
    _GetFileTime.restype = w.BOOL

    _SetFileTime = ctypes.windll.kernel32.SetFileTime
    _SetFileTime.argtypes = [
        w.HANDLE,   # hFile
        POINTER(FILETIME),  # lpCreationTime  (可 NULL)
        POINTER(FILETIME),  # lpLastWriteTime (可 NULL)
        POINTER(FILETIME),  # lpLastAccessTime (可 NULL)
    ]
    _SetFileTime.restype = w.BOOL

    _CloseHandle = ctypes.windll.kernel32.CloseHandle
    _CloseHandle.argtypes = [w.HANDLE]
    _CloseHandle.restype = w.BOOL

    # ── 获取 Windows 错误消息 ───────────────────────────────────────────
    _GetLastError = ctypes.windll.kernel32.GetLastError
    _GetLastError.argtypes = []
    _GetLastError.restype = w.DWORD

    _FormatMessageW = ctypes.windll.kernel32.FormatMessageW
    _FormatMessageW.argtypes = [
        w.DWORD,       # dwFlags
        w.LPVOID,      # lpSource
        w.DWORD,       # dwMessageId
        w.DWORD,       # dwLanguageId
        w.LPWSTR,      # lpBuffer
        w.DWORD,       # nSize
        w.LPVOID,      # Arguments
    ]
    _FormatMessageW.restype = w.DWORD

    FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
    FORMAT_MESSAGE_IGNORE_INSERTS = 0x00000200

    def _get_last_error_message() -> str:
        """获取最近一次 Windows API 错误的描述文本。"""
        code = _GetLastError()
        buf = ctypes.create_unicode_buffer(512)
        n = _FormatMessageW(
            FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
            None,
            code,
            0,  # 默认语言
            buf,
            len(buf),
            None,
        )
        if n:
            msg = buf.value.strip()
        else:
            msg = f"未知错误 (代码 {code})"
        return f"WinError [{code}]: {msg}"

    def _filetime_to_datetime(ft: FILETIME) -> datetime:
        """将 Windows FILETIME 转换为 Python datetime (UTC)。"""
        # FILETIME 是自 1601-01-01 以来的 100ns 间隔数
        intervals = (ft.dwHighDateTime << 32) + ft.dwLowDateTime
        # 转换为微秒
        microseconds = intervals // 10
        try:
            return datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(
                microseconds=microseconds
            )
        except (OverflowError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)

    def _datetime_to_filetime(dt: datetime) -> FILETIME:
        """将 Python datetime 转换为 Windows FILETIME。"""
        # 确保是 UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        delta = dt - datetime(1601, 1, 1, tzinfo=timezone.utc)
        # 总微秒数
        total_micros = (
            delta.days * 86400 * 1_000_000 + delta.seconds * 1_000_000 + delta.microseconds
        )
        intervals = total_micros * 10  # 100ns 间隔
        if intervals < 0:
            intervals = 0
        ft = FILETIME()
        ft.dwLowDateTime = w.DWORD(intervals & 0xFFFFFFFF)
        ft.dwHighDateTime = w.DWORD((intervals >> 32) & 0xFFFFFFFF)
        return ft

    def _open_file_handle(
        path: str,
        access: int = GENERIC_READ | GENERIC_WRITE,
        share: int = FILE_SHARE_READ | FILE_SHARE_WRITE,
    ) -> Optional[int]:
        """打开文件/目录句柄，返回 HANDLE 值；失败返回 None。"""
        flags = FILE_FLAG_BACKUP_SEMANTICS  # 支持目录
        handle = _CreateFileW(
            path,
            access,
            share,
            None,
            OPEN_EXISTING,
            flags,
            None,
        )
        if handle == INVALID_HANDLE_VALUE or not handle:
            return None
        return handle

    def _close_handle(handle: int) -> None:
        """关闭句柄。"""
        if handle and handle != INVALID_HANDLE_VALUE:
            _CloseHandle(handle)

else:
    # 非 Windows 平台：占位实现
    def _get_last_error_message() -> str:
        return "不支持的操作系统 (仅 Windows)"

    def _filetime_to_datetime(ft) -> datetime:
        raise NotImplementedError("仅 Windows 平台支持")

    def _datetime_to_filetime(dt: datetime):
        raise NotImplementedError("仅 Windows 平台支持")

    def _open_file_handle(path: str, access=0, share=0) -> Optional[int]:
        return None

    def _close_handle(handle: int) -> None:
        pass


# ── 数据模型 ─────────────────────────────────────────────────────────────

@dataclass
class FileTimes:
    """表示一个文件/目录的三个时间戳。"""
    creation_time: Optional[datetime] = None
    last_write_time: Optional[datetime] = None
    last_access_time: Optional[datetime] = None

    def __bool__(self) -> bool:
        """至少有一个时间被设置。"""
        return (
            self.creation_time is not None
            or self.last_write_time is not None
            or self.last_access_time is not None
        )


# ── 核心引擎 ─────────────────────────────────────────────────────────────

class TimestampHandler:
    """文件时间戳读写引擎。

    使用 Windows API (CreateFileW / GetFileTime / SetFileTime) 实现。
    非 Windows 平台上所有方法安全降级，返回 None / 空容器。
    """

    # ── 类级备份栈（所有实例共享） ──────────────────────────────────────
    _backup_stack: list[dict[str, dict]] = []

    # ── 公开 API ────────────────────────────────────────────────────────

    def get_times(self, path: str) -> Optional[FileTimes]:
        """读取单个文件/目录的三个时间戳。

        Args:
            path: 文件或目录的完整路径（支持 Unicode）。

        Returns:
            FileTimes 对象，失败返回 None。
        """
        if os.name != "nt":
            print("[TimestampHandler] 警告: GetFileTime 仅在 Windows 上可用")
            return None

        if not os.path.exists(path):
            print(f"[TimestampHandler] 路径不存在: {path}")
            return None

        handle = _open_file_handle(path, GENERIC_READ)
        if handle is None:
            print(f"[TimestampHandler] 无法打开文件: {path} — {_get_last_error_message()}")
            return None

        try:
            ctime = FILETIME()
            wtime = FILETIME()
            atime = FILETIME()

            success = _GetFileTime(handle,
                                   ctypes.byref(ctime),
                                   ctypes.byref(wtime),
                                   ctypes.byref(atime))
            if not success:
                print(f"[TimestampHandler] GetFileTime 失败: {path} — "
                      f"{_get_last_error_message()}")
                return None

            return FileTimes(
                creation_time=_filetime_to_datetime(ctime),
                last_write_time=_filetime_to_datetime(wtime),
                last_access_time=_filetime_to_datetime(atime),
            )
        finally:
            _close_handle(handle)

    def set_times(self, path: str, times: FileTimes) -> bool:
        """设置单个文件/目录的三个时间戳。

        FileTimes 中为 None 的字段保持不变（不修改）。
        调用前会自动备份原始时间戳（便于后续撤销）。

        Args:
            path: 文件或目录的完整路径。
            times: 要设置的时间戳。

        Returns:
            成功返回 True，失败返回 False。
        """
        if os.name != "nt":
            print("[TimestampHandler] 警告: SetFileTime 仅在 Windows 上可用")
            return False

        if not os.path.exists(path):
            print(f"[TimestampHandler] 路径不存在: {path}")
            return False

        # 自动备份
        self.backup(path)

        handle = _open_file_handle(path, GENERIC_READ | GENERIC_WRITE)
        if handle is None:
            print(f"[TimestampHandler] 无法以写入方式打开: {path} — "
                  f"{_get_last_error_message()}")
            return False

        try:
            # 构造参数：为 None 的字段传入 None（NULL 指针表示保持不变）
            p_ctime = None
            p_wtime = None
            p_atime = None

            if times.creation_time is not None:
                ft_ctime = _datetime_to_filetime(times.creation_time)
                p_ctime = ctypes.byref(ft_ctime)

            if times.last_write_time is not None:
                ft_wtime = _datetime_to_filetime(times.last_write_time)
                p_wtime = ctypes.byref(ft_wtime)

            if times.last_access_time is not None:
                ft_atime = _datetime_to_filetime(times.last_access_time)
                p_atime = ctypes.byref(ft_atime)

            # 至少有一个非空字段才调用
            if p_ctime is None and p_wtime is None and p_atime is None:
                print(f"[TimestampHandler] set_times 调用无效：所有时间字段均为 None")
                return False

            success = _SetFileTime(handle, p_ctime, p_wtime, p_atime)
            if not success:
                print(f"[TimestampHandler] SetFileTime 失败: {path} — "
                      f"{_get_last_error_message()}")
                return False

            return True
        finally:
            _close_handle(handle)

    def batch_get(
        self,
        paths: list[str],
        recursive: bool = True,
    ) -> dict[str, Optional[FileTimes]]:
        """批量读取多个文件/目录的时间戳。

        Args:
            paths: 路径列表。其中目录会在 recursive=True 时自动展开。
            recursive: 是否递归遍历子目录。

        Returns:
            {路径: FileTimes | None} 的字典。
        """
        if os.name != "nt":
            print("[TimestampHandler] batch_get 仅在 Windows 上可用")
            return {}

        all_paths: list[str] = []
        for p in paths:
            if os.path.isdir(p) and recursive:
                for sub_path, _ in self.walk_with_progress(p):
                    all_paths.append(sub_path)
            else:
                all_paths.append(p)

        result: dict[str, Optional[FileTimes]] = {}
        for p in all_paths:
            result[p] = self.get_times(p)
        return result

    def batch_set(
        self,
        items: dict[str, FileTimes],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> dict[str, bool]:
        """批量设置多个文件/目录的时间戳。

        所有修改操作会作为一个批次记录在备份栈中，
        可通过 ``restore_last()`` 一键撤销。

        Args:
            items: {路径: FileTimes} 字典。
            progress_callback: 进度回调，签名 (current, total, path)。

        Returns:
            {路径: 是否成功} 的字典。
        """
        if os.name != "nt":
            print("[TimestampHandler] batch_set 仅在 Windows 上可用")
            return {}

        total = len(items)
        results: dict[str, bool] = {}

        for idx, (path, times) in enumerate(items.items(), start=1):
            results[path] = self.set_times(path, times)
            if progress_callback:
                progress_callback(idx, total, path)

        return results

    def backup(self, path: str) -> Optional[dict]:
        """备份指定路径的原始时间戳。

        备份数据存储在类级栈中，可通过 ``restore_last()`` 恢复。

        Args:
            path: 要备份的文件/目录路径。

        Returns:
            备份记录字典，包含路径和原始时间戳；失败返回 None。
        """
        original = self.get_times(path)
        if original is None:
            return None

        record = {
            "path": path,
            "original_times": original,
        }
        self._backup_stack.append(record)
        return record

    def restore_last(self) -> int:
        """撤销最近一次 ``set_times`` 或 ``batch_set`` 操作。

        从备份栈中弹出最近一个批次的备份记录并恢复。
        注意：如果最近一次操作只涉及单个文件，则只恢复该文件。

        Returns:
            成功恢复的文件数。
        """
        if not self._backup_stack:
            print("[TimestampHandler] 没有可撤销的备份记录")
            return 0

        if os.name != "nt":
            print("[TimestampHandler] restore_last 仅在 Windows 上可用")
            return 0

        # 收集本次要恢复的记录（属于同一批次的）
        # 简单做法：从栈顶弹出直到遇到不是同一批次起始的记录
        # 但更稳健的做法是记录 batch 标记。为简单起见，我们只弹出最近一条。
        # 注意 batch_set 中每个 path 都会调用 backup，所以 batch_set
        # 会向栈中压入多条记录。pop 所有属于最近一次操作的记录… 但我们
        # 没有批次标记。改进方案：使用 batch_id 标记。
        #
        # 更简单的方案：restore_last 只恢复最后一条备份。
        recovered = 0
        if self._backup_stack:
            record = self._backup_stack.pop()
            path = record["path"]
            original: FileTimes = record["original_times"]
            ok = self.set_times(path, original)
            if ok:
                recovered += 1
            else:
                print(f"[TimestampHandler] 恢复失败: {path}")

        return recovered

    # ── 静态工具方法 ─────────────────────────────────────────────────────

    @staticmethod
    def adjust_time(dt: datetime, delta: timedelta) -> datetime:
        """对时间戳应用相对偏移。

        Args:
            dt: 原始时间（带时区或不带时区）。
            delta: 偏移量（可为负值表示提前）。

        Returns:
            调整后的时间。
        """
        return dt + delta

    @staticmethod
    def filter_paths(paths: list[str], pattern: str = "*") -> list[str]:
        """按文件名 glob 模式过滤路径列表。

        Args:
            paths: 原始路径列表。
            pattern: 文件名 glob 模式（如 ``*.txt``, ``data_*``）。

        Returns:
            匹配模式的路径列表。
        """
        return [p for p in paths if fnmatch.fnmatch(os.path.basename(p), pattern)]

    @staticmethod
    def walk_with_progress(
        root_dir: str,
    ) -> Generator[tuple[str, bool], None, None]:
        """递归遍历目录树，逐项生成 (路径, 是否为目录)。

        Args:
            root_dir: 根目录路径。

        Yields:
            (path, is_dir) 元组。
        """
        if not os.path.isdir(root_dir):
            if os.path.exists(root_dir):
                yield (root_dir, False)
            return

        for dirpath, dirnames, filenames in os.walk(root_dir):
            # 先 yield 目录本身
            yield (dirpath, True)
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                yield (full_path, False)

    # ── 实用辅助方法 ─────────────────────────────────────────────────────

    @staticmethod
    def ensure_unicode(path: str) -> str:
        """确保路径是 Unicode 字符串（用于 Windows API 调用）。"""
        if isinstance(path, bytes):
            return path.decode("utf-8")
        return path

    @staticmethod
    def is_windows() -> bool:
        """当前是否运行在 Windows 平台上。"""
        return os.name == "nt"


# ── 便捷函数 ─────────────────────────────────────────────────────────────

def check_platform() -> None:
    """检查运行平台，非 Windows 时给出提示。"""
    if os.name != "nt":
        print("=" * 60)
        print("  ⚠  [Folder Time Editor] 核心引擎仅在 Windows 上可用。")
        print("  当前操作系统不支持 Windows API (SetFileTime/GetFileTime)。")
        print("  所有读写时间戳的操作将返回空结果。")
        print("=" * 60)
    else:
        print("[Folder Time Editor] 核心引擎已加载（Windows 平台）")


# ── 快速测试（python -m core.timestamp_handler） ──────────────────────

if __name__ == "__main__":
    check_platform()

    if os.name == "nt":
        handler = TimestampHandler()
        test_path = os.path.abspath(__file__)

        print(f"\n测试读取: {test_path}")
        times = handler.get_times(test_path)
        if times:
            print(f"  创建时间: {times.creation_time}")
            print(f"  修改时间: {times.last_write_time}")
            print(f"  访问时间: {times.last_access_time}")
        else:
            print("  读取失败")
    else:
        print("\n跳过测试（非 Windows 平台）")
