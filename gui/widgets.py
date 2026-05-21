"""Custom widgets for FolderTimeEditor.

Provides:
  - DatePicker: calendar date selection
  - TimeEntry: time input field
  - DateTimePicker: combined date + time widget
  - PathTreeView: file/folder list with columns
  - LogWidget: colored log output
  - StatusBar: progress + stats bar
"""
from __future__ import annotations

import calendar
import os
import tkinter as tk
from datetime import datetime, date, time, timedelta
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

import ttkbootstrap as tb
from ttkbootstrap.constants import *


# ── DatePicker ──────────────────────────────────────────────────────────────

class DatePicker(tb.Frame):
    """A date entry widget with a dropdown calendar.

    Displays a text entry bound to yyyy-MM-dd format and a calendar popup
    for visual date selection.
    """

    DATE_FORMAT = '%Y-%m-%d'

    def __init__(
        self,
        master,
        date_var: Optional[tk.StringVar] = None,
        command: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._command = command
        self._calendar_window: Optional[tk.Toplevel] = None
        self._sel_year = datetime.now().year
        self._sel_month = datetime.now().month

        # Variable
        if date_var is None:
            date_var = tk.StringVar(value=datetime.now().strftime(self.DATE_FORMAT))
        self.date_var = date_var

        # Build UI
        self.entry = tb.Entry(self, textvariable=self.date_var, width=14, state='readonly')
        self.entry.pack(side=LEFT, fill=X, expand=True)

        self.btn = tb.Button(
            self,
            text='📅',
            bootstyle='secondary-outline',
            command=self._toggle_calendar,
            width=3,
        )
        self.btn.pack(side=LEFT, padx=(2, 0))

    # ── public API ──────────────────────────────────────────────────────

    def get_date(self) -> Optional[date]:
        try:
            return datetime.strptime(self.date_var.get(), self.DATE_FORMAT).date()
        except (ValueError, TypeError):
            return None

    def set_date(self, d: date):
        self.date_var.set(d.strftime(self.DATE_FORMAT))

    # ── calendar popup ──────────────────────────────────────────────────

    def _toggle_calendar(self):
        if self._calendar_window and self._calendar_window.winfo_exists():
            self._calendar_window.destroy()
            self._calendar_window = None
        else:
            self._open_calendar()

    def _open_calendar(self):
        self._calendar_window = tk.Toplevel(self)
        self._calendar_window.title('选择日期')
        self._calendar_window.resizable(False, False)
        self._calendar_window.transient(self.winfo_toplevel())
        self._calendar_window.grab_set()

        # Position near the button
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self._calendar_window.geometry(f'+{x}+{y}')

        # Parse current date
        cur = self.get_date() or date.today()
        self._sel_year = cur.year
        self._sel_month = cur.month

        self._build_calendar_content()

    def _build_calendar_content(self):
        win = self._calendar_window
        for w in win.winfo_children():
            w.destroy()

        # Navigation header
        nav = tb.Frame(win)
        nav.pack(fill=X, padx=4, pady=4)

        tb.Button(nav, text='◀', width=3, bootstyle='secondary-outline',
                  command=lambda: self._shift_month(-1)).pack(side=LEFT)
        self._month_label = tb.Label(nav, text='', font=('Segoe UI', 11, 'bold'),
                                     anchor=CENTER)
        self._month_label.pack(side=LEFT, fill=X, expand=True)
        tb.Button(nav, text='▶', width=3, bootstyle='secondary-outline',
                  command=lambda: self._shift_month(1)).pack(side=LEFT)

        # Calendar grid
        cal_frame = tb.Frame(win)
        cal_frame.pack(padx=6, pady=(0, 6))

        # Day headers
        days = ['一', '二', '三', '四', '五', '六', '日']
        for col, d in enumerate(days):
            lbl = tb.Label(cal_frame, text=d, font=('Segoe UI', 9),
                           width=3, anchor=CENTER)
            lbl.grid(row=0, column=col, padx=1, pady=1)

        self._refresh_calendar_days(cal_frame)

    def _refresh_calendar_days(self, parent):
        self._month_label.config(
            text=f'{self._sel_year}年{self._sel_month:02d}月'
        )

        # Remove old day buttons (keep header row 0)
        for w in parent.grid_slaves():
            if int(w.grid_info()['row']) > 0:
                w.destroy()

        cal = calendar.Calendar(firstweekday=0)  # Monday first
        month_days = cal.monthdayscalendar(self._sel_year, self._sel_month)

        today = date.today()
        sel = self.get_date()

        for r, week in enumerate(month_days, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    lbl = tb.Label(parent, text='', width=4)
                    lbl.grid(row=r, column=c, padx=1, pady=1)
                else:
                    d = date(self._sel_year, self._sel_month, day)
                    btn = tb.Button(
                        parent,
                        text=str(day),
                        width=3,
                        padding=0,
                        bootstyle='secondary-link',
                        command=lambda dt=d: self._select_date(dt),
                    )
                    # Highlight today
                    if d == today:
                        btn.configure(bootstyle='primary')
                    # Highlight current selection
                    if sel and d == sel:
                        btn.configure(bootstyle='success')
                    btn.grid(row=r, column=c, padx=1, pady=1)

    def _shift_month(self, delta: int):
        self._sel_month += delta
        if self._sel_month < 1:
            self._sel_month = 12
            self._sel_year -= 1
        elif self._sel_month > 12:
            self._sel_month = 1
            self._sel_year += 1
        self._build_calendar_content()

    def _select_date(self, d: date):
        self.set_date(d)
        if self._command:
            self._command(d.strftime(self.DATE_FORMAT))
        if self._calendar_window:
            self._calendar_window.destroy()
            self._calendar_window = None


# ── TimeEntry ──────────────────────────────────────────────────────────────

class TimeEntry(tb.Frame):
    """A time input with formatted entry and spin controls.

    Format: HH:mm:ss (24-hour)
    """

    def __init__(self, master, time_var: Optional[tk.StringVar] = None, **kwargs):
        super().__init__(master, **kwargs)

        if time_var is None:
            time_var = tk.StringVar(value='00:00:00')
        self.time_var = time_var
        self._validate_cmd = self.register(self._validate_time)

        self.entry = tb.Entry(
            self,
            textvariable=self.time_var,
            width=10,
            validate='focusout',
            validatecommand=(self._validate_cmd, '%P'),
        )
        self.entry.pack(side=LEFT, fill=X, expand=True)

        # Spin buttons
        self._up_btn = tb.Button(
            self, text='▲', width=2, padding=0,
            bootstyle='secondary-outline', command=self._spin_up,
        )
        self._up_btn.pack(side=LEFT, padx=(1, 0))

        self._down_btn = tb.Button(
            self, text='▼', width=2, padding=0,
            bootstyle='secondary-outline', command=self._spin_down,
        )
        self._down_btn.pack(side=LEFT, padx=(0, 0))

    def get_time(self) -> Optional[time]:
        try:
            parts = self.time_var.get().strip().split(':')
            return time(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return None

    def set_time(self, t: time):
        self.time_var.set(t.strftime('%H:%M:%S'))

    def _validate_time(self, value: str) -> bool:
        try:
            parts = value.strip().split(':')
            if len(parts) != 3:
                return False
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return 0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59
        except (ValueError, IndexError):
            return False

    def _spin_up(self):
        t = self.get_time() or time(0, 0, 0)
        total = t.hour * 3600 + t.minute * 60 + t.second + 1
        if total >= 86400:
            total = 0
        self.set_time(time(total // 3600, (total % 3600) // 60, total % 60))

    def _spin_down(self):
        t = self.get_time() or time(0, 0, 0)
        total = t.hour * 3600 + t.minute * 60 + t.second - 1
        if total < 0:
            total = 86399
        self.set_time(time(total // 3600, (total % 3600) // 60, total % 60))


# ── DateTimePicker ─────────────────────────────────────────────────────────

class DateTimePicker(tb.Frame):
    """Combined date + time picker.

    Returns a `datetime` object or None.
    """

    def __init__(
        self,
        master,
        label_text: str = '',
        dt_var: Optional[tk.StringVar] = None,
        show_sync: bool = True,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        if dt_var is None:
            dt_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self._dt_var = dt_var

        # ── enable checkbox ──
        self.enabled_var = tk.BooleanVar(value=True)
        self.enabled_cb = tb.Checkbutton(
            self, variable=self.enabled_var, text='',
            bootstyle='round-toggle',
            command=self._on_enable_toggle,
        )
        self.enabled_cb.pack(side=LEFT, padx=(0, 2))

        # ── label ──
        self.label = tb.Label(self, text=label_text, width=8, anchor=W)
        self.label.pack(side=LEFT)

        # ── mode: absolute / relative ──
        self.mode_var = tk.StringVar(value='absolute')
        self._mode_frame = tb.Frame(self)
        self._mode_frame.pack(side=LEFT, padx=2)

        self._abs_rb = tb.Radiobutton(
            self._mode_frame, text='绝对', variable=self.mode_var,
            value='absolute', bootstyle='info-outline-toolbutton',
            command=self._on_mode_change,
        )
        self._abs_rb.pack(side=LEFT)

        self._rel_rb = tb.Radiobutton(
            self._mode_frame, text='相对', variable=self.mode_var,
            value='relative', bootstyle='info-outline-toolbutton',
            command=self._on_mode_change,
        )
        self._rel_rb.pack(side=LEFT)

        # ── absolute date-time frame ──
        self._abs_frame = tb.Frame(self)
        self._abs_frame.pack(side=LEFT, fill=X, expand=True)

        self._date_picker = DatePicker(self._abs_frame, date_var=tk.StringVar())
        self._date_picker.pack(side=LEFT, padx=1)

        self._time_entry = TimeEntry(self._abs_frame, time_var=tk.StringVar())
        self._time_entry.pack(side=LEFT, padx=1)

        # ── relative spinbox frame ──
        self._rel_frame = tb.Frame(self)

        self._days_var = tk.IntVar(value=0)
        self._hours_var = tk.IntVar(value=0)
        self._mins_var = tk.IntVar(value=0)

        for label, var, fmt in [
            ('天', self._days_var, '{:d}'),
            ('时', self._hours_var, '{:d}'),
            ('分', self._mins_var, '{:d}'),
        ]:
            f = tb.Frame(self._rel_frame)
            f.pack(side=LEFT, padx=2)
            tb.Label(f, text=label, font=('Segoe UI', 9)).pack(side=LEFT)
            sb = tb.Spinbox(
                f, from_=-999, to=999, width=5,
                textvariable=var, format=fmt,
                bootstyle='secondary',
            )
            sb.pack(side=LEFT)

        # Show/hide initial state
        self._sync_var = tk.BooleanVar(value=False)

        self._on_mode_change()

    # ── public API ──────────────────────────────────────────────────────

    def get_enabled(self) -> bool:
        return self.enabled_var.get()

    def set_enabled(self, enabled: bool):
        self.enabled_var.set(enabled)
        self._on_enable_toggle()

    def get_datetime(self) -> Optional[datetime]:
        """Get the resulting datetime (absolute mode) or None."""
        if not self.enabled_var.get():
            return None

        if self.mode_var.get() == 'absolute':
            d = self._date_picker.get_date()
            t = self._time_entry.get_time()
            if d and t:
                return datetime.combine(d, t)
            return None
        return None  # relative mode: not a fixed datetime

    def get_rel_delta(self) -> Optional[timedelta]:
        """Get relative adjustment as timedelta (relative mode)."""
        if not self.enabled_var.get() or self.mode_var.get() != 'relative':
            return None
        return timedelta(
            days=self._days_var.get(),
            hours=self._hours_var.get(),
            minutes=self._mins_var.get(),
        )

    def get_rel_seconds(self) -> Optional[int]:
        delta = self.get_rel_delta()
        if delta is None:
            return None
        return int(delta.total_seconds())

    def get_mode(self) -> str:
        return self.mode_var.get()

    def set_datetime(self, dt: datetime):
        self._date_picker.set_date(dt.date())
        self._time_entry.set_time(dt.time())

    def bind_sync(self, var: tk.BooleanVar):
        """Bind to a shared sync variable."""
        self._sync_var = var

    # ── internal ────────────────────────────────────────────────────────

    def _on_enable_toggle(self):
        enabled = self.enabled_var.get()
        state = NORMAL if enabled else DISABLED
        for w in (self._abs_frame, self._rel_frame, self._mode_frame):
            for child in w.winfo_children():
                try:
                    child.configure(state=state)
                except Exception:
                    pass

    def _on_mode_change(self):
        if self.mode_var.get() == 'absolute':
            self._abs_frame.pack(side=LEFT, fill=X, expand=True)
            self._rel_frame.pack_forget()
        else:
            self._abs_frame.pack_forget()
            self._rel_frame.pack(side=LEFT, fill=X, expand=True)
        self._on_enable_toggle()


# ── PathTreeView ───────────────────────────────────────────────────────────

class PathTreeView(tb.Frame):
    """Treeview displaying file/folder paths with metadata columns.

    Columns: 文件名, 路径, 创建时间, 修改时间, 访问时间, 大小
    """

    COLUMNS = ('name', 'path', 'creation_time', 'modification_time',
               'access_time', 'size')
    HEADINGS = {
        'name': '文件名',
        'path': '路径',
        'creation_time': '创建时间',
        'modification_time': '修改时间',
        'access_time': '访问时间',
        'size': '大小',
    }
    COL_WIDTHS = {
        'name': 200,
        'path': 350,
        'creation_time': 160,
        'modification_time': 160,
        'access_time': 160,
        'size': 90,
    }

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._items: List[dict] = []  # list of {column: value, ...}
        self._selected_indices: set = set()

        # Build treeview
        self.tree = ttk.Treeview(
            self,
            columns=list(self.COLUMNS),
            show='headings',
            selectmode='extended',
            bootstyle='primary',
        )

        # Scrollbars
        v_scroll = ttk.Scrollbar(self, orient=VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self, orient=HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky=NSEW)
        v_scroll.grid(row=0, column=1, sticky=NS)
        h_scroll.grid(row=1, column=0, sticky=EW)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Configure columns
        for col_id in self.COLUMNS:
            self.tree.heading(col_id, text=self.HEADINGS[col_id],
                              command=lambda c=col_id: self._sort_by(c))
            self.tree.column(col_id, width=self.COL_WIDTHS[col_id],
                             minwidth=60, anchor=W if col_id != 'size' else E)

        # Right-click menu
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label='移除选中', command=self.remove_selected)
        self._menu.add_command(label='清空全部', command=self.clear_all)
        self._menu.add_separator()
        self._menu.add_command(label='全选', command=self.select_all)

        self.tree.bind('<Button-3>', self._show_context_menu)
        self.tree.bind('<Control-a>', lambda e: self.select_all())

    # ── public API ──────────────────────────────────────────────────────

    def add_items(self, items: List[dict]):
        """Add items to the treeview.

        Each dict must have keys matching COLUMNS.
        """
        for item in items:
            self._items.append(item)
            self.tree.insert('', END, values=tuple(item.get(c, '') for c in self.COLUMNS))

    def get_selected(self) -> List[dict]:
        """Return dicts of selected rows."""
        sel = self.tree.selection()
        indices = [self.tree.index(iid) for iid in sel]
        return [self._items[i] for i in indices]

    def get_all(self) -> List[dict]:
        return list(self._items)

    def remove_selected(self):
        sel = self.tree.selection()
        # Remove in reverse order to preserve indices
        for iid in reversed(sel):
            idx = self.tree.index(iid)
            self.tree.delete(iid)
            if idx < len(self._items):
                self._items.pop(idx)

    def clear_all(self):
        self.tree.delete(*self.tree.get_children())
        self._items.clear()

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def item_count(self) -> int:
        return len(self._items)

    def get_paths(self) -> List[str]:
        return [item.get('path', '') for item in self._items]

    # ── internal ────────────────────────────────────────────────────────

    def _sort_by(self, col: str):
        """Sort treeview by column (simple text sort)."""
        children = self.tree.get_children('')
        if not children:
            return

        items = [(self.tree.set(child, col), child) for child in children]
        items.sort(key=lambda x: x[0])
        for idx, (_, child) in enumerate(items):
            self.tree.move(child, '', idx)

    def _show_context_menu(self, event):
        try:
            self._menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu.grab_release()


# ── LogWidget ──────────────────────────────────────────────────────────────

class LogWidget(tb.Frame):
    """Colored log output widget.

    Supports tags for info (gray), success (green), error (red), warning (yellow).
    """

    STYLES = {
        'info': ('gray', 'white'),
        'success': ('green', 'white'),
        'error': ('red', 'white'),
        'warning': ('orange', 'white'),
    }

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.text = tk.Text(
            self,
            wrap=WORD,
            state=DISABLED,
            font=('Consolas', 10),
            bg='#1a1a2e',
            fg='#c0c0c0',
            insertbackground='white',
            relief=FLAT,
            borderwidth=0,
            padx=6,
            pady=6,
        )

        v_scroll = ttk.Scrollbar(self, orient=VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=v_scroll.set)

        self.text.pack(side=LEFT, fill=BOTH, expand=True)
        v_scroll.pack(side=RIGHT, fill=Y)

        # Configure tags
        self.text.tag_configure('timestamp', foreground='#6c757d')
        for tag, (fg, bg) in self.STYLES.items():
            self.text.tag_configure(tag, foreground=fg)

    def log(self, message: str, level: str = 'info'):
        """Append a timestamped log message."""
        now = datetime.now().strftime('%H:%M:%S')
        self.text.configure(state=NORMAL)
        self.text.insert(END, f'[{now}] ', 'timestamp')
        self.text.insert(END, message + '\n', level)
        self.text.see(END)
        self.text.configure(state=DISABLED)

    def info(self, msg: str):
        self.log(msg, 'info')

    def success(self, msg: str):
        self.log(msg, 'success')

    def error(self, msg: str):
        self.log(msg, 'error')

    def warning(self, msg: str):
        self.log(msg, 'warning')

    def clear(self):
        self.text.configure(state=NORMAL)
        self.text.delete('1.0', END)
        self.text.configure(state=DISABLED)


# ── StatusBar ──────────────────────────────────────────────────────────────

class StatusBar(tb.Frame):
    """Bottom status bar with progress and statistics."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Progress bar
        self.progress = ttk.Progressbar(
            self, mode='determinate', value=0, length=200,
        )
        self.progress.pack(side=LEFT, padx=5, pady=2, fill=X, expand=True)

        # Stats label
        self.stats_var = tk.StringVar(value='已处理 0/0，成功 0，失败 0')
        self.stats_label = tb.Label(self, textvariable=self.stats_var,
                                    font=('Segoe UI', 10), bootstyle='inverse-secondary')
        self.stats_label.pack(side=LEFT, padx=(10, 5))

    def set_progress(self, value: float, maximum: float = 100):
        if maximum > 0:
            self.progress['maximum'] = maximum
        self.progress['value'] = value
        self.update_idletasks()

    def set_stats(self, processed: int, total: int, succeeded: int, failed: int):
        self.stats_var.set(f'已处理 {processed}/{total}，成功 {succeeded}，失败 {failed}')

    def reset(self):
        self.progress['value'] = 0
        self.stats_var.set('已处理 0/0，成功 0，失败 0')
