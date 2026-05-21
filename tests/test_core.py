"""Unit tests for core.timestamp_handler — FileTimes & TimestampHandler.

Tests are split into two categories:
  1. Platform-independent tests — run on any OS (Linux, macOS, Windows).
  2. Windows-API tests — mock ctypes/kernel32 to simulate Windows behavior.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# ── Module under test ──────────────────────────────────────────────────────
# Ensure the project root is on sys.path for import
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core import FileTimes, TimestampHandler
from core.timestamp_handler import check_platform


# ═══════════════════════════════════════════════════════════════════════════
#  1.  Data model — FileTimes
# ═══════════════════════════════════════════════════════════════════════════

class TestFileTimes:
    """FileTimes dataclass creation and __bool__ semantics."""

    def test_create_empty(self):
        """FileTimes with no arguments — all fields None."""
        ft = FileTimes()
        assert ft.creation_time is None
        assert ft.last_write_time is None
        assert ft.last_access_time is None
        assert not ft  # __bool__ → False

    def test_create_creation_only(self):
        """FileTimes with only creation_time set."""
        dt = datetime(2025, 1, 15, 10, 30, 0)
        ft = FileTimes(creation_time=dt)
        assert ft.creation_time == dt
        assert ft.last_write_time is None
        assert ft.last_access_time is None
        assert ft  # __bool__ → True

    def test_create_write_only(self):
        """FileTimes with only last_write_time set."""
        dt = datetime(2025, 6, 1, 12, 0, 0)
        ft = FileTimes(last_write_time=dt)
        assert ft.creation_time is None
        assert ft.last_write_time == dt
        assert ft.last_access_time is None
        assert ft

    def test_create_access_only(self):
        """FileTimes with only last_access_time set."""
        dt = datetime(2025, 3, 20, 8, 15, 30)
        ft = FileTimes(last_access_time=dt)
        assert ft.creation_time is None
        assert ft.last_write_time is None
        assert ft.last_access_time == dt
        assert ft

    def test_create_all_fields(self):
        """FileTimes with all three timestamps."""
        c = datetime(2024, 12, 1, 0, 0, 0)
        w = datetime(2025, 1, 15, 14, 30, 0)
        a = datetime(2025, 2, 10, 9, 0, 0)
        ft = FileTimes(creation_time=c, last_write_time=w, last_access_time=a)
        assert ft.creation_time == c
        assert ft.last_write_time == w
        assert ft.last_access_time == a
        assert ft

    def test_bool_false_when_all_none(self):
        """__bool__ returns False when all fields are None."""
        ft = FileTimes(None, None, None)
        assert not ft

    def test_bool_true_with_creation(self):
        """__bool__ returns True when only creation_time is set."""
        ft = FileTimes(creation_time=datetime.now())
        assert ft

    def test_bool_true_with_write(self):
        """__bool__ returns True when only last_write_time is set."""
        ft = FileTimes(last_write_time=datetime.now())
        assert ft

    def test_bool_true_with_access(self):
        """__bool__ returns True when only last_access_time is set."""
        ft = FileTimes(last_access_time=datetime.now())
        assert ft

    def test_dataclass_repr(self):
        """FileTimes has a readable repr."""
        dt = datetime(2025, 6, 1, 12, 0, 0)
        ft = FileTimes(creation_time=dt)
        r = repr(ft)
        assert "FileTimes" in r
        assert "creation_time" in r

    def test_dataclass_equality(self):
        """FileTimes supports equality comparison."""
        dt = datetime(2025, 6, 1, 12, 0, 0)
        ft1 = FileTimes(creation_time=dt)
        ft2 = FileTimes(creation_time=dt)
        assert ft1 == ft2
        ft3 = FileTimes(creation_time=datetime(2025, 1, 1, 0, 0, 0))
        assert ft1 != ft3


# ═══════════════════════════════════════════════════════════════════════════
#  2.  Static utility methods — platform-independent
# ═══════════════════════════════════════════════════════════════════════════

class TestAdjustTime:
    """TimestampHandler.adjust_time — static method."""

    def test_positive_delta(self):
        """Adding a positive timedelta."""
        dt = datetime(2025, 6, 1, 12, 0, 0)
        delta = timedelta(hours=3, minutes=30)
        result = TimestampHandler.adjust_time(dt, delta)
        assert result == datetime(2025, 6, 1, 15, 30, 0)

    def test_negative_delta(self):
        """Adding a negative timedelta (going backward)."""
        dt = datetime(2025, 6, 1, 12, 0, 0)
        delta = timedelta(days=-5)
        result = TimestampHandler.adjust_time(dt, delta)
        assert result == datetime(2025, 5, 27, 12, 0, 0)

    def test_zero_delta(self):
        """Adding zero timedelta — unchanged."""
        dt = datetime(2025, 6, 1, 12, 0, 0)
        delta = timedelta(0)
        result = TimestampHandler.adjust_time(dt, delta)
        assert result == dt

    def test_large_delta_forward(self):
        """Large positive delta across year boundary."""
        dt = datetime(2025, 12, 25, 0, 0, 0)
        delta = timedelta(days=30)
        result = TimestampHandler.adjust_time(dt, delta)
        assert result == datetime(2026, 1, 24, 0, 0, 0)

    def test_large_delta_backward(self):
        """Large negative delta across year boundary."""
        dt = datetime(2025, 1, 5, 0, 0, 0)
        delta = timedelta(days=-10)
        result = TimestampHandler.adjust_time(dt, delta)
        assert result == datetime(2024, 12, 26, 0, 0, 0)

    def test_with_timezone_aware(self):
        """Adjustment works with timezone-aware datetimes."""
        dt = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        delta = timedelta(hours=1)
        result = TimestampHandler.adjust_time(dt, delta)
        assert result == datetime(2025, 6, 1, 13, 0, 0, tzinfo=timezone.utc)

    def test_microseconds(self):
        """Adjustment preserves microseconds."""
        dt = datetime(2025, 6, 1, 12, 0, 0, 500000)
        delta = timedelta(microseconds=250000)
        result = TimestampHandler.adjust_time(dt, delta)
        assert result.microsecond == 750000


class TestFilterPaths:
    """TimestampHandler.filter_paths — static method."""

    def test_exact_match(self):
        """Exact filename pattern."""
        paths = ["/tmp/data.txt", "/tmp/readme.md", "/tmp/script.py"]
        result = TimestampHandler.filter_paths(paths, "data.txt")
        assert result == ["/tmp/data.txt"]

    def test_wildcard_txt(self):
        """Glob pattern *.txt."""
        paths = ["a.txt", "b.csv", "c.txt", "d.log"]
        result = TimestampHandler.filter_paths(paths, "*.txt")
        assert result == ["a.txt", "c.txt"]

    def test_wildcard_prefix(self):
        """Prefix glob pattern."""
        paths = ["/app/log_2025.txt", "/app/log_2024.txt", "/app/data.csv"]
        result = TimestampHandler.filter_paths(paths, "log_*")
        assert result == ["/app/log_2025.txt", "/app/log_2024.txt"]

    def test_empty_list(self):
        """Empty input list returns empty list."""
        result = TimestampHandler.filter_paths([], "*")
        assert result == []

    def test_no_match(self):
        """No paths match the pattern."""
        paths = ["a.py", "b.py"]
        result = TimestampHandler.filter_paths(paths, "*.md")
        assert result == []

    def test_match_all(self):
        """Default pattern '*' matches everything."""
        paths = ["x.txt", "y.csv", "z.py"]
        result = TimestampHandler.filter_paths(paths)
        assert result == paths

    def test_directories_in_path(self):
        """Pattern matches basename only, not full path."""
        paths = ["/home/user/docs/report.txt", "/home/user/pics/photo.jpg"]
        result = TimestampHandler.filter_paths(paths, "*.txt")
        assert result == ["/home/user/docs/report.txt"]

    def test_path_with_dots(self):
        """Paths with multiple dots in names."""
        paths = ["/a/b.c/file.name.txt", "/a/b.c/file.name.csv"]
        result = TimestampHandler.filter_paths(paths, "*.txt")
        assert result == ["/a/b.c/file.name.txt"]


class TestWalkWithProgress:
    """TimestampHandler.walk_with_progress — static generator."""

    def test_single_file(self, tmp_path):
        """Walking a single file yields one item."""
        f = tmp_path / "test.txt"
        f.write_text("hello")
        results = list(TimestampHandler.walk_with_progress(str(f)))
        assert len(results) == 1
        assert results[0] == (str(f), False)

    def test_empty_directory(self, tmp_path):
        """Walking an empty directory yields only the directory itself."""
        d = tmp_path / "empty_dir"
        d.mkdir()
        results = list(TimestampHandler.walk_with_progress(str(d)))
        assert len(results) == 1
        assert results[0] == (str(d), True)

    def test_directory_with_files(self, tmp_path):
        """Walking a directory with files yields dir + files."""
        d = tmp_path / "my_dir"
        d.mkdir()
        f1 = d / "a.txt"
        f1.write_text("a")
        f2 = d / "b.txt"
        f2.write_text("b")
        results = list(TimestampHandler.walk_with_progress(str(d)))
        # Order: dir first, then files in os.walk order
        assert results[0] == (str(d), True)
        paths = {p for p, is_dir in results}
        assert str(f1) in paths
        assert str(f2) in paths

    def test_nested_directories(self, tmp_path):
        """Walking nested directories yields all levels."""
        d = tmp_path / "root"
        sub = d / "sub"
        sub.mkdir(parents=True)
        f = sub / "nested.txt"
        f.write_text("data")
        results = list(TimestampHandler.walk_with_progress(str(d)))
        paths_found = {p for p, _ in results}
        assert str(d) in paths_found
        assert str(sub) in paths_found
        assert str(f) in paths_found

    def test_nonexistent_path(self, tmp_path):
        """Walking a non-existent path yields nothing."""
        p = tmp_path / "does_not_exist"
        results = list(TimestampHandler.walk_with_progress(str(p)))
        assert results == []

    def test_file_with_no_directory(self, tmp_path):
        """Walking a file when it's a file yields the file."""
        f = tmp_path / "standalone.py"
        f.write_text("code")
        results = list(TimestampHandler.walk_with_progress(str(f)))
        assert len(results) == 1
        assert results[0][1] is False  # is_dir = False

    def test_multiple_subdirectories(self, tmp_path):
        """Walking with multiple subdirectories and files."""
        root = tmp_path / "multi"
        a = root / "A"
        b = root / "B"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        (a / "a1.txt").write_text("1")
        (b / "b1.txt").write_text("2")
        results = list(TimestampHandler.walk_with_progress(str(root)))
        # Check all expected paths exist
        dirs_found = {p for p, is_dir in results if is_dir}
        files_found = {p for p, is_dir in results if not is_dir}
        assert str(root) in dirs_found
        assert str(a) in dirs_found
        assert str(b) in dirs_found
        assert len(files_found) == 2


# ═══════════════════════════════════════════════════════════════════════════
#  3.  Utility / helper methods
# ═══════════════════════════════════════════════════════════════════════════

class TestEnsureUnicode:
    """TimestampHandler.ensure_unicode — static method."""

    def test_bytes_input(self):
        """Bytes input is decoded to str."""
        result = TimestampHandler.ensure_unicode(b"/path/to/file")
        assert isinstance(result, str)
        assert result == "/path/to/file"

    def test_str_input(self):
        """String input is returned as-is."""
        path = "/path/to/file"
        result = TimestampHandler.ensure_unicode(path)
        assert result is path

    def test_unicode_chars(self):
        """Unicode characters in string are preserved."""
        path = "/路径/文件.txt"
        result = TimestampHandler.ensure_unicode(path)
        assert result == path

    def test_bytes_with_unicode(self):
        """Bytes with UTF-8 encoded Unicode."""
        path = "/路径/文件.txt"
        result = TimestampHandler.ensure_unicode(path.encode("utf-8"))
        assert result == path

    def test_empty_string(self):
        """Empty string input."""
        assert TimestampHandler.ensure_unicode("") == ""

    def test_empty_bytes(self):
        """Empty bytes input."""
        assert TimestampHandler.ensure_unicode(b"") == ""


class TestIsWindows:
    """TimestampHandler.is_windows — static method."""

    def test_on_linux_returns_false(self):
        """On Linux, is_windows() returns False."""
        assert TimestampHandler.is_windows() is False

    def test_mocked_returns_true(self, monkeypatch):
        """When os.name is mocked to 'nt', is_windows() returns True."""
        monkeypatch.setattr(os, "name", "nt")
        assert TimestampHandler.is_windows() is True


class TestCheckPlatform:
    """check_platform() function."""

    def test_on_linux_prints_warning(self, capsys):
        """On Linux, check_platform prints a warning message."""
        check_platform()
        captured = capsys.readouterr()
        assert "仅在 Windows 上可用" in captured.out
        assert "Windows" in captured.out

    def test_mocked_windows_prints_ok(self, capsys, monkeypatch):
        """When os.name is mocked to 'nt', check_platform prints OK."""
        monkeypatch.setattr(os, "name", "nt")
        check_platform()
        captured = capsys.readouterr()
        assert "核心引擎已加载" in captured.out


# ═══════════════════════════════════════════════════════════════════════════
#  4.  Module-level exports
# ═══════════════════════════════════════════════════════════════════════════

class TestModuleExports:
    """Verify core/__init__.py exports the expected symbols."""

    def test_FileTimes_exported(self):
        """FileTimes is importable from core."""
        from core import FileTimes
        assert FileTimes is not None

    def test_TimestampHandler_exported(self):
        """TimestampHandler is importable from core."""
        from core import TimestampHandler
        assert TimestampHandler is not None

    def test_all_contains_both(self):
        """__all__ lists both FileTimes and TimestampHandler."""
        from core import __all__
        assert "FileTimes" in __all__
        assert "TimestampHandler" in __all__


# ═══════════════════════════════════════════════════════════════════════════
#  5.  TimestampHandler instance methods — on Linux (graceful degradation)
# ═══════════════════════════════════════════════════════════════════════════

class TestTimestampHandlerOnLinux:
    """TimestampHandler methods on non-Windows platforms return None/empty."""

    def setup_method(self):
        self.handler = TimestampHandler()

    def test_get_times_returns_none(self, capsys):
        """get_times on Linux returns None."""
        result = self.handler.get_times(__file__)
        assert result is None
        captured = capsys.readouterr()
        assert "仅在 Windows 上可用" in captured.out

    def test_get_times_nonexistent_path(self, capsys, monkeypatch):
        """On Windows mock, get_times checks path existence."""
        monkeypatch.setattr(os, "name", "nt")
        result = self.handler.get_times("/nonexistent/path/xyz")
        assert result is None
        captured = capsys.readouterr()
        assert "路径不存在" in captured.out

    def test_set_times_returns_false(self, capsys):
        """set_times on Linux returns False."""
        ft = FileTimes(creation_time=datetime.now())
        result = self.handler.set_times(__file__, ft)
        assert result is False
        captured = capsys.readouterr()
        assert "仅在 Windows 上可用" in captured.out

    def test_batch_get_returns_empty(self, capsys):
        """batch_get on Linux returns empty dict."""
        result = self.handler.batch_get([__file__])
        assert result == {}
        captured = capsys.readouterr()
        assert "仅在 Windows 上可用" in captured.out

    def test_batch_set_returns_empty(self, capsys):
        """batch_set on Linux returns empty dict."""
        result = self.handler.batch_set({})
        assert result == {}
        captured = capsys.readouterr()
        assert "仅在 Windows 上可用" in captured.out

    def test_backup_returns_none(self):
        """backup on Linux returns None."""
        result = self.handler.backup(__file__)
        assert result is None

    def test_restore_last_returns_zero(self):
        """restore_last on Linux returns 0."""
        result = self.handler.restore_last()
        assert result == 0

    def test_ensure_unicode_static(self):
        """ensure_unicode works as static method on Linux."""
        result = TimestampHandler.ensure_unicode(b"hello")
        assert result == "hello"


# ═══════════════════════════════════════════════════════════════════════════
#  6.  Windows API tests — fully mocked
# ═══════════════════════════════════════════════════════════════════════════

class TestTimestampHandlerWindowsMock:
    """Simulate Windows environment with mocked ctypes.windll.kernel32.

    All tests in this class carefully mock os.name, ctypes.windll, and the
    internal helper functions so we can verify the Windows code paths without
    actually calling any Win32 APIs.
    """

    def _make_mock_kernel32(self):
        """Create a mock kernel32 module with all required functions."""
        k32 = MagicMock()

        # CreateFileW: return a valid handle
        k32.CreateFileW.return_value = 12345  # fake HANDLE

        # GetFileTime: return success
        k32.GetFileTime.return_value = True

        # SetFileTime: return success
        k32.SetFileTime.return_value = True

        # CloseHandle: return success
        k32.CloseHandle.return_value = True

        # GetLastError: return 0
        k32.GetLastError.return_value = 0

        # FormatMessageW: return a message
        k32.FormatMessageW.return_value = 0  # no message formatted

        return k32

    def _setup_module_patches(self, monkeypatch, mock_kernel32=None):
        """Set up Windows mocking environment at the module level.

        On Linux, the Windows-only symbols (_CreateFileW, etc.) are not
        defined in the module because they live inside an ``if os.name == 'nt':``
        block.  We must *add* them to the module object so that the Windows
        code paths in get_times / set_times can resolve them at runtime.

        Strategy:
          1. Patch os.name → 'nt'
          2. Add all Windows API callables / constants to the module
          3. Mock _open_file_handle / _close_handle / conversion functions
        """
        if mock_kernel32 is None:
            mock_kernel32 = self._make_mock_kernel32()

        import core.timestamp_handler as th

        monkeypatch.setattr(os, "name", "nt")

        # Helper: add attributes that don't exist on the Linux module build
        def _add_attr(name, value):
            monkeypatch.setattr(th, name, value, raising=False)

        # Add Windows API function references (not present on Linux builds)
        _add_attr("_CreateFileW", mock_kernel32.CreateFileW)
        _add_attr("_GetFileTime", mock_kernel32.GetFileTime)
        _add_attr("_SetFileTime", mock_kernel32.SetFileTime)
        _add_attr("_CloseHandle", mock_kernel32.CloseHandle)
        _add_attr("_GetLastError", mock_kernel32.GetLastError)
        _add_attr("_FormatMessageW", mock_kernel32.FormatMessageW)

        # Add Windows constants (not present on Linux builds)
        _add_attr("GENERIC_READ", 0x80000000)
        _add_attr("GENERIC_WRITE", 0x40000000)
        _add_attr("FILE_SHARE_READ", 0x00000001)
        _add_attr("FILE_SHARE_WRITE", 0x00000002)
        _add_attr("OPEN_EXISTING", 3)
        _add_attr("FILE_FLAG_BACKUP_SEMANTICS", 0x02000000)
        _add_attr("INVALID_HANDLE_VALUE", -1)

        # Provide a simple FILETIME-like class
        class FakeFILETIME:
            _fields_ = [("dwLowDateTime", int), ("dwHighDateTime", int)]
            dwLowDateTime = 1000
            dwHighDateTime = 0

        _add_attr("FILETIME", FakeFILETIME)

        # Mock file-handle functions (they have stubs on Linux, so they exist)
        monkeypatch.setattr(th, "_open_file_handle", MagicMock(return_value=12345))
        monkeypatch.setattr(th, "_close_handle", MagicMock())

        # Mock conversion functions (they have stubs on Linux, so they exist)
        fake_dt = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        monkeypatch.setattr(th, "_filetime_to_datetime", MagicMock(return_value=fake_dt))

        def fake_dt_to_filetime(dt):
            ft = FakeFILETIME()
            ft.dwLowDateTime = 2000
            ft.dwHighDateTime = 0
            return ft

        monkeypatch.setattr(th, "_datetime_to_filetime", fake_dt_to_filetime)
        monkeypatch.setattr(th, "_get_last_error_message", MagicMock(
            return_value="Mocked error message"))

        # Also need ctypes.byref to work with our fake FILETIME.
        # On Linux, `ctypes` is not a module-level name (it's inside the
        # `if os.name == 'nt':` block).  We add a mock ctypes where byref
        # always returns a MagicMock to avoid real ctypes type-checking.
        mock_ctypes = MagicMock()
        mock_ctypes.byref = MagicMock(return_value=MagicMock())
        _add_attr("ctypes", mock_ctypes)

        return mock_kernel32, th

    def test_get_times_mocked(self, monkeypatch):
        """get_times returns FileTimes when Windows APIs are mocked."""
        _, th = self._setup_module_patches(monkeypatch)

        handler = th.TimestampHandler()
        # Create a real file for path existence check
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name

        try:
            result = handler.get_times(tmp_path)
            assert result is not None
            assert isinstance(result, th.FileTimes)
            assert result.creation_time == datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
            assert result.last_write_time == datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
            assert result.last_access_time == datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        finally:
            os.unlink(tmp_path)

    def test_get_times_failure_mocked(self, monkeypatch):
        """get_times returns None on Windows API failure."""
        mock_k32 = self._make_mock_kernel32()
        mock_k32.GetFileTime.return_value = False  # API failure
        _, th = self._setup_module_patches(monkeypatch, mock_k32)

        handler = th.TimestampHandler()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        try:
            result = handler.get_times(tmp_path)
            assert result is None
        finally:
            os.unlink(tmp_path)

    def test_set_times_mocked(self, monkeypatch):
        """set_times returns True when Windows APIs are mocked."""
        mock_k32 = self._make_mock_kernel32()
        mock_k32.SetFileTime.return_value = True
        _, th = self._setup_module_patches(monkeypatch, mock_k32)

        handler = th.TimestampHandler()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        try:
            ft = th.FileTimes(creation_time=datetime(2025, 6, 1, 12, 0, 0))
            result = handler.set_times(tmp_path, ft)
            assert result is True
        finally:
            os.unlink(tmp_path)

    def test_set_times_failure_mocked(self, monkeypatch):
        """set_times returns False on Windows API failure."""
        mock_k32 = self._make_mock_kernel32()
        mock_k32.SetFileTime.return_value = False  # API failure
        _, th = self._setup_module_patches(monkeypatch, mock_k32)

        handler = th.TimestampHandler()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        try:
            ft = th.FileTimes(creation_time=datetime(2025, 6, 1, 12, 0, 0))
            result = handler.set_times(tmp_path, ft)
            assert result is False
        finally:
            os.unlink(tmp_path)

    def test_set_times_all_none(self, monkeypatch):
        """set_times with all-None FileTimes returns False."""
        _, th = self._setup_module_patches(monkeypatch)

        handler = th.TimestampHandler()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        try:
            ft = th.FileTimes()  # all None
            result = handler.set_times(tmp_path, ft)
            assert result is False
        finally:
            os.unlink(tmp_path)

    def test_batch_get_mocked(self, monkeypatch):
        """batch_get returns FileTimes dict when mocked."""
        _, th = self._setup_module_patches(monkeypatch)

        handler = th.TimestampHandler()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        try:
            results = handler.batch_get([tmp_path], recursive=False)
            assert tmp_path in results
            assert results[tmp_path] is not None
            assert isinstance(results[tmp_path], th.FileTimes)
        finally:
            os.unlink(tmp_path)

    def test_batch_set_mocked(self, monkeypatch):
        """batch_set returns success dict when mocked."""
        _, th = self._setup_module_patches(monkeypatch)

        handler = th.TimestampHandler()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        try:
            ft = th.FileTimes(creation_time=datetime(2025, 6, 1, 12, 0, 0))
            results = handler.batch_set({tmp_path: ft})
            assert tmp_path in results
            assert results[tmp_path] is True
        finally:
            os.unlink(tmp_path)

    def test_batch_set_with_progress_callback(self, monkeypatch):
        """batch_set calls progress_callback for each item."""
        _, th = self._setup_module_patches(monkeypatch)

        handler = th.TimestampHandler()
        calls = []

        def progress(current, total, path):
            calls.append((current, total, path))

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        try:
            ft = th.FileTimes(creation_time=datetime(2025, 6, 1, 12, 0, 0))
            results = handler.batch_set({tmp_path: ft}, progress_callback=progress)
            assert len(calls) == 1
            assert calls[0] == (1, 1, tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_backup_and_restore_mocked(self, monkeypatch):
        """backup stores data, restore_last restores it."""
        _, th = self._setup_module_patches(monkeypatch)

        handler = th.TimestampHandler()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            tmp_path = f.name
        try:
            ft = th.FileTimes(creation_time=datetime(2025, 6, 1, 12, 0, 0))

            # First set — triggers backup
            ok = handler.set_times(tmp_path, ft)
            assert ok is True

            # Now restore
            recovered = handler.restore_last()
            assert recovered == 1
        finally:
            os.unlink(tmp_path)

    def test_restore_last_no_backup(self, monkeypatch):
        """restore_last with empty backup stack returns 0."""
        _, th = self._setup_module_patches(monkeypatch)

        handler = th.TimestampHandler()
        # Reset backup stack
        handler._backup_stack.clear()
        result = handler.restore_last()
        assert result == 0

    def test_restore_last_non_windows_returns_zero(self, capsys):
        """restore_last on non-Windows returns 0 even with backup data."""
        handler = TimestampHandler()
        # Manually push backup data
        handler._backup_stack.append({
            "path": __file__,
            "original_times": FileTimes(creation_time=datetime.now())
        })
        result = handler.restore_last()
        assert result == 0
        captured = capsys.readouterr()
        assert "仅在 Windows 上可用" in captured.out
