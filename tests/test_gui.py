"""GUI module tests for FolderTimeEditor.

Most GUI tests require a display (tkinter root window). On headless CI
environments (no $DISPLAY), these tests are skipped with a clear message.

Where possible, we do basic import verification and class existence checks
that don't require instantiation.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure the project root is on sys.path for import
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ═══════════════════════════════════════════════════════════════════════════
#  1.  Module import tests (no display required)
# ═══════════════════════════════════════════════════════════════════════════

class TestGuiImports:
    """Verify all GUI modules can be imported without errors."""

    def test_gui_package_import(self):
        """gui package __init__ imports correctly."""
        import gui
        assert hasattr(gui, "FolderTimeEditor")

    def test_gui_app_module_import(self):
        """gui.app module imports correctly."""
        from gui import app
        assert app is not None

    def test_gui_dialogs_module_import(self):
        """gui.dialogs module imports correctly."""
        from gui import dialogs
        assert dialogs is not None

    def test_gui_widgets_module_import(self):
        """gui.widgets module imports correctly."""
        from gui import widgets
        assert widgets is not None

    def test_main_module_import(self):
        """main.py module imports correctly."""
        import main
        assert hasattr(main, "main")


class TestGuiClassExistence:
    """Check that expected classes exist in their modules."""

    def test_FolderTimeEditor_class_exists(self):
        """FolderTimeEditor main window class exists."""
        from gui.app import FolderTimeEditor
        assert isinstance(FolderTimeEditor, type)

    def test_PreviewDialog_class_exists(self):
        """PreviewDialog class exists."""
        from gui.dialogs import PreviewDialog
        assert isinstance(PreviewDialog, type)

    def test_ProfileDialog_class_exists(self):
        """ProfileDialog class exists."""
        from gui.dialogs import ProfileDialog
        assert isinstance(ProfileDialog, type)

    def test_DateTimePicker_class_exists(self):
        """DateTimePicker widget class exists."""
        from gui.widgets import DateTimePicker
        assert isinstance(DateTimePicker, type)

    def test_PathTreeView_class_exists(self):
        """PathTreeView widget class exists."""
        from gui.widgets import PathTreeView
        assert isinstance(PathTreeView, type)

    def test_LogWidget_class_exists(self):
        """LogWidget class exists."""
        from gui.widgets import LogWidget
        assert isinstance(LogWidget, type)

    def test_StatusBar_class_exists(self):
        """StatusBar class exists."""
        from gui.widgets import StatusBar
        assert isinstance(StatusBar, type)

    def test_DatePicker_class_exists(self):
        """DatePicker widget class exists."""
        from gui.widgets import DatePicker
        assert isinstance(DatePicker, type)

    def test_TimeEntry_class_exists(self):
        """TimeEntry widget class exists."""
        from gui.widgets import TimeEntry
        assert isinstance(TimeEntry, type)

    def test_gui_all_export(self):
        """gui.__init__ exports FolderTimeEditor in __all__."""
        import gui
        assert "FolderTimeEditor" in gui.__all__


class TestGuiConstantsAndBasics:
    """Check constants, docstrings, and basic module attributes."""

    def test_app_has_docstring(self):
        """gui.app module has a docstring."""
        from gui import app
        assert app.__doc__ is not None
        assert len(app.__doc__) > 10

    def test_dialogs_has_docstring(self):
        """gui.dialogs module has a docstring."""
        from gui import dialogs
        assert dialogs.__doc__ is not None
        assert len(dialogs.__doc__) > 10

    def test_widgets_has_docstring(self):
        """gui.widgets module has a docstring."""
        from gui import widgets
        assert widgets.__doc__ is not None
        assert len(widgets.__doc__) > 10

    def test_LogWidget_styles_defined(self):
        """LogWidget has STYLES dict with required keys."""
        from gui.widgets import LogWidget
        for key in ("info", "success", "error", "warning"):
            assert key in LogWidget.STYLES

    def test_PathTreeView_columns_defined(self):
        """PathTreeView has COLUMNS tuple."""
        from gui.widgets import PathTreeView
        assert len(PathTreeView.COLUMNS) >= 5
        assert "name" in PathTreeView.COLUMNS
        assert "path" in PathTreeView.COLUMNS

    def test_DateTimePicker_has_datetime_api(self):
        """DateTimePicker has expected public methods."""
        from gui.widgets import DateTimePicker
        assert hasattr(DateTimePicker, "get_datetime")
        assert hasattr(DateTimePicker, "get_enabled")
        assert hasattr(DateTimePicker, "get_mode")
        assert hasattr(DateTimePicker, "set_datetime")

    def test_FolderTimeEditor_format_size(self):
        """FolderTimeEditor._format_size returns correct human-readable strings."""
        from gui.app import FolderTimeEditor
        assert FolderTimeEditor._format_size(0) == "0 B"
        assert FolderTimeEditor._format_size(500) == "500 B"
        assert FolderTimeEditor._format_size(1024) == "1.0 KB"
        assert FolderTimeEditor._format_size(1536) == "1.5 KB"
        assert FolderTimeEditor._format_size(1048576) == "1.0 MB"
        assert FolderTimeEditor._format_size(1073741824) == "1.00 GB"


# ═══════════════════════════════════════════════════════════════════════════
#  2.  GUI Widget instantiation tests — require display & tkroot
# ═══════════════════════════════════════════════════════════════════════════

_has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
_no_display_reason = "需要显示器 (tkinter); 无 DISPLAY 环境变量"


@pytest.fixture(scope="session")
def _tk_root_session():
    """Session-scoped tkinter root so ttkbootstrap style is created only once.

    ttkbootstrap caches its Style instance globally; destroying and recreating
    the root between tests causes ``TclError: application has been destroyed``.
    A session-scoped fixture avoids this problem entirely.
    """
    # These widgets depend on ttkbootstrap, which requires a root window.
    import tkinter as tk
    import ttkbootstrap as tb

    root = tb.Window(themename="superhero")
    root.withdraw()
    yield root
    root.destroy()


@pytest.mark.skipif(not _has_display, reason=_no_display_reason)
class TestWidgetInstantiation:
    """Instantiate GUI widgets with a real tkinter root.

    These tests require a running X server / display.  On CI without
    a virtual framebuffer, the entire class is skipped.
    """

    @pytest.fixture(autouse=True)
    def _tk_root(self, _tk_root_session):
        """Use the session-scoped root for each test."""
        return _tk_root_session

    def test_DatePicker_instantiate(self, _tk_root):
        """DatePicker can be instantiated."""
        from gui.widgets import DatePicker
        w = DatePicker(_tk_root)
        assert w is not None

    def test_TimeEntry_instantiate(self, _tk_root):
        """TimeEntry can be instantiated."""
        from gui.widgets import TimeEntry
        w = TimeEntry(_tk_root)
        assert w is not None

    def test_DateTimePicker_instantiate(self, _tk_root):
        """DateTimePicker can be instantiated."""
        from gui.widgets import DateTimePicker
        w = DateTimePicker(_tk_root, label_text="测试")
        assert w is not None
        assert w.get_enabled() is True

    def test_DateTimePicker_get_datetime(self, _tk_root):
        """DateTimePicker.get_datetime returns None before any date set.

        Note: the DateTimePicker sub-widgets (DatePicker, TimeEntry) are
        initialized with empty StringVars, so get_datetime() returns None
        until the user interacts with the widget or set_datetime() is called.
        """
        from gui.widgets import DateTimePicker
        w = DateTimePicker(_tk_root, label_text="测试")
        # Initially returns None because sub-pickers have empty values
        assert w.get_datetime() is None
        # After setting, returns a valid datetime
        from datetime import datetime
        dt = datetime(2025, 6, 1, 10, 30, 0)
        w.set_datetime(dt)
        result = w.get_datetime()
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 1
        assert result.hour == 10
        assert result.minute == 30

    def test_DateTimePicker_set_datetime(self, _tk_root):
        """DateTimePicker.set_datetime updates the displayed value."""
        from datetime import datetime
        from gui.widgets import DateTimePicker
        w = DateTimePicker(_tk_root, label_text="测试")
        new_dt = datetime(2025, 6, 1, 12, 30, 0)
        w.set_datetime(new_dt)
        result = w.get_datetime()
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 30

    def test_DateTimePicker_disable(self, _tk_root):
        """DateTimePicker can be disabled."""
        from gui.widgets import DateTimePicker
        w = DateTimePicker(_tk_root, label_text="测试")
        w.set_enabled(False)
        assert w.get_enabled() is False
        assert w.get_datetime() is None

    def test_LogWidget_instantiate(self, _tk_root):
        """LogWidget can be instantiated."""
        from gui.widgets import LogWidget
        w = LogWidget(_tk_root)
        assert w is not None

    def test_LogWidget_log_methods(self, _tk_root):
        """LogWidget info/success/error/warning methods work."""
        from gui.widgets import LogWidget
        w = LogWidget(_tk_root)
        w.info("info test")
        w.success("success test")
        w.error("error test")
        w.warning("warning test")
        assert True

    def test_LogWidget_clear(self, _tk_root):
        """LogWidget.clear removes all text."""
        from gui.widgets import LogWidget
        w = LogWidget(_tk_root)
        w.info("some message")
        w.clear()
        content = w.text.get("1.0", "end-1c")
        assert content == ""

    def test_StatusBar_instantiate(self, _tk_root):
        """StatusBar can be instantiated."""
        from gui.widgets import StatusBar
        w = StatusBar(_tk_root)
        assert w is not None

    def test_StatusBar_set_progress(self, _tk_root):
        """StatusBar.set_progress updates value."""
        from gui.widgets import StatusBar
        w = StatusBar(_tk_root)
        w.set_progress(50, 100)
        assert w.progress["value"] == 50

    def test_StatusBar_set_stats(self, _tk_root):
        """StatusBar.set_stats updates stats label."""
        from gui.widgets import StatusBar
        w = StatusBar(_tk_root)
        w.set_stats(10, 20, 8, 2)
        assert "10/20" in w.stats_var.get()
        assert "8" in w.stats_var.get()
        assert "2" in w.stats_var.get()

    def test_StatusBar_reset(self, _tk_root):
        """StatusBar.reset clears progress and stats."""
        from gui.widgets import StatusBar
        w = StatusBar(_tk_root)
        w.set_progress(75, 100)
        w.set_stats(15, 20, 14, 1)
        w.reset()
        assert w.progress["value"] == 0
        assert "0/0" in w.stats_var.get()

    def test_PathTreeView_instantiate(self, _tk_root):
        """PathTreeView can be instantiated."""
        from gui.widgets import PathTreeView
        w = PathTreeView(_tk_root)
        assert w is not None

    def test_PathTreeView_add_and_count(self, _tk_root):
        """PathTreeView.add_items and item_count work."""
        from gui.widgets import PathTreeView
        w = PathTreeView(_tk_root)
        items = [
            {"name": "a.txt", "path": "/tmp/a.txt", "creation_time": "",
             "modification_time": "", "access_time": "", "size": "100 B"},
            {"name": "b.txt", "path": "/tmp/b.txt", "creation_time": "",
             "modification_time": "", "access_time": "", "size": "200 B"},
        ]
        w.add_items(items)
        assert w.item_count() == 2

    def test_PathTreeView_get_all(self, _tk_root):
        """PathTreeView.get_all returns all items."""
        from gui.widgets import PathTreeView
        w = PathTreeView(_tk_root)
        items = [
            {"name": "a.txt", "path": "/tmp/a.txt", "creation_time": "",
             "modification_time": "", "access_time": "", "size": "100 B"},
        ]
        w.add_items(items)
        all_items = w.get_all()
        assert len(all_items) == 1
        assert all_items[0]["name"] == "a.txt"

    def test_PathTreeView_clear_all(self, _tk_root):
        """PathTreeView.clear_all removes all items."""
        from gui.widgets import PathTreeView
        w = PathTreeView(_tk_root)
        items = [
            {"name": "a.txt", "path": "/tmp/a.txt", "creation_time": "",
             "modification_time": "", "access_time": "", "size": "100 B"},
        ]
        w.add_items(items)
        w.clear_all()
        assert w.item_count() == 0

    def test_PathTreeView_get_paths(self, _tk_root):
        """PathTreeView.get_paths returns all paths."""
        from gui.widgets import PathTreeView
        w = PathTreeView(_tk_root)
        items = [
            {"name": "a.txt", "path": "/tmp/a.txt", "creation_time": "",
             "modification_time": "", "access_time": "", "size": "100 B"},
            {"name": "b.txt", "path": "/tmp/b.txt", "creation_time": "",
             "modification_time": "", "access_time": "", "size": "200 B"},
        ]
        w.add_items(items)
        paths = w.get_paths()
        assert paths == ["/tmp/a.txt", "/tmp/b.txt"]


@pytest.mark.skipif(not _has_display, reason=_no_display_reason)
class TestMainWindow:
    """Test the main FolderTimeEditor window (requires display).

    The application's ``__init__`` calls ``tb.dialogs.show_question`` on
    non-Windows platforms, which does not exist in all ttkbootstrap versions.
    We mock it to avoid the error.
    """

    @pytest.fixture(autouse=True)
    def _app(self):
        """Create application instance for testing.

        The app calls ``tb.dialogs.show_question`` on non-Windows which does
        not exist in this ttkbootstrap version; we monkey-patch it.
        """
        import gui.app
        with patch.object(gui.app.tb.dialogs, "show_question",
                          create=True, return_value=True):
            from gui.app import FolderTimeEditor
            app = FolderTimeEditor()
            app.withdraw()
            app.update_idletasks()
            yield app
            app.destroy()

    def test_app_creation(self, _app):
        """Application window can be created."""
        assert _app is not None
        assert _app.title() == "FolderTimeEditor - 文件夹时间批量修改工具"

    def test_app_has_handler(self, _app):
        """Application has a TimestampHandler instance."""
        assert _app.handler is not None

    def test_app_has_path_tree(self, _app):
        """Application has path_tree widget."""
        assert _app.path_tree is not None

    def test_app_has_log(self, _app):
        """Application has log widget."""
        assert _app.log is not None

    def test_app_has_status_bar(self, _app):
        """Application has status bar."""
        assert _app.status_bar is not None

    def test_app_has_dt_pickers(self, _app):
        """Application has datetime pickers."""
        assert _app._creation_picker is not None
        assert _app._modification_picker is not None
        assert _app._access_picker is not None

    def test_app_get_bg(self, _app):
        """_get_bg returns a color string."""
        bg = _app._get_bg()
        assert isinstance(bg, str)
        assert bg.startswith("#")

    def test_app_count_var(self, _app):
        """_count_var shows initial count of 0."""
        assert _app._count_var.get() == "共 0 项"
