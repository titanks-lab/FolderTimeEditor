"""Main application window for FolderTimeEditor.

Provides a modern GUI for batch-modifying file/folder timestamps on Windows.
Built with tkinter + ttkbootstrap.
"""
from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, ttk
from typing import Any, Dict, List, Optional

import ttkbootstrap as tb
from ttkbootstrap.constants import *

from core.timestamp_handler import TimestampHandler, FileTimes

from .dialogs import PreviewDialog, ProfileDialog
from .widgets import (
    DateTimePicker,
    LogWidget,
    PathTreeView,
    StatusBar,
)


class FolderTimeEditor(tb.Window):
    """Main application window.

    Theme: superhero (dark), 1200x800 default, DPI-aware.
    """

    def __init__(self):
        super().__init__(themename='superhero')

        # ── platform check ──
        if sys.platform != 'win32':
            tb.dialogs.Messagebox.show_question(
                title='平台提示',
                message='此工具仅支持 Windows 平台。\n当前系统：' + sys.platform,
            )

        # ── window setup ──
        self.title('FolderTimeEditor - 文件夹时间批量修改工具')
        self.geometry('1200x800')
        self.minsize(1000, 600)

        # Center window
        self._center_window()

        # DPI scaling
        try:
            scaling = self.tk.call('tk', 'scaling')
            if scaling < 1.2:
                self.tk.call('tk', 'scaling', 1.5)
        except Exception:
            pass

        # ── core engine ──
        self.handler = TimestampHandler()

        # ── state ──
        self._undo_available = False
        self._last_plan: List[Dict[str, Any]] = []

        # ── build UI ──
        self._build_menu()
        self._build_main_layout()
        self._build_status_bar()

        # ── key bindings ──
        self.bind('<Control-o>', lambda e: self._add_folder())
        self.bind('<Control-f>', lambda e: self._add_file())
        self.bind('<Escape>', lambda e: self._on_escape())

        # ── drag-drop setup ──
        self._setup_drag_drop()

    # ═════════════════════════════════════════════════════════════════════
    # Layout Construction
    # ═════════════════════════════════════════════════════════════════════

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f'{w}x{h}+{x}+{y}')

    def _build_menu(self):
        """Build the top menu bar."""
        menubar = tk.Menu(self)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='添加文件夹...', command=self._add_folder,
                              accelerator='Ctrl+O')
        file_menu.add_command(label='添加文件...', command=self._add_file,
                              accelerator='Ctrl+F')
        file_menu.add_separator()
        file_menu.add_command(label='保存时间方案...', command=self._save_profile)
        file_menu.add_command(label='加载时间方案...', command=self._load_profile)
        file_menu.add_separator()
        file_menu.add_command(label='退出', command=self.quit)
        menubar.add_cascade(label='文件', menu=file_menu)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label='移除选中', command=self._remove_selected)
        edit_menu.add_command(label='清空列表', command=self._clear_list)
        edit_menu.add_separator()
        edit_menu.add_command(label='全选', command=self._select_all,
                              accelerator='Ctrl+A')
        menubar.add_cascade(label='编辑', menu=edit_menu)

        # Action menu
        action_menu = tk.Menu(menubar, tearoff=0)
        action_menu.add_command(label='预览修改', command=self._preview_changes)
        action_menu.add_command(label='执行修改', command=self._apply_changes,
                                accelerator='Ctrl+Enter')
        action_menu.add_command(label='撤销上次', command=self._undo_changes)
        menubar.add_cascade(label='操作', menu=action_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label='关于', command=self._show_about)
        menubar.add_cascade(label='帮助', menu=help_menu)

        self.config(menu=menubar)

    def _build_main_layout(self):
        """Build the main content area with left/right or top/bottom panels."""
        # Main horizontal paned window
        self._paned = tb.Panedwindow(self, orient=HORIZONTAL)
        self._paned.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # ── Left: file/folder list ──
        left_frame = tb.Frame(self._paned)
        self._paned.add(left_frame, weight=3)

        self._build_file_list_panel(left_frame)

        # ── Right: time settings ──
        right_frame = tb.Frame(self._paned)
        self._paned.add(right_frame, weight=2)

        self._build_time_settings_panel(right_frame)

        # ── Bottom: log area ──
        # (Separated below the paned window)
        self._build_log_panel()

    def _build_file_list_panel(self, parent):
        """Build the file/folder list panel (left side)."""
        # ── Toolbar ──
        toolbar = tb.Frame(parent)
        toolbar.pack(fill=X, padx=5, pady=(5, 2))

        tb.Button(
            toolbar, text='📁  添加文件夹', bootstyle='secondary-outline',
            command=self._add_folder, width=16,
        ).pack(side=LEFT, padx=2)

        tb.Button(
            toolbar, text='📄  添加文件', bootstyle='secondary-outline',
            command=self._add_file, width=16,
        ).pack(side=LEFT, padx=2)

        tb.Button(
            toolbar, text='🗑  移除选中', bootstyle='danger-outline',
            command=self._remove_selected, width=12,
        ).pack(side=LEFT, padx=2)

        tb.Button(
            toolbar, text='🧹  清空', bootstyle='secondary-outline',
            command=self._clear_list, width=8,
        ).pack(side=LEFT, padx=2)

        # Count label
        self._count_var = tk.StringVar(value='共 0 项')
        tb.Label(toolbar, textvariable=self._count_var,
                 font=('Segoe UI', 10)).pack(side=RIGHT, padx=5)

        # ── Treeview ──
        self.path_tree = PathTreeView(parent)
        self.path_tree.pack(fill=BOTH, expand=True, padx=5, pady=2)

    def _build_time_settings_panel(self, parent):
        """Build the time settings panel (right side)."""
        # Scrollable area in case of many controls
        canvas = tk.Canvas(parent, highlightthickness=0, bg=self._get_bg())
        v_scroll = ttk.Scrollbar(parent, orient=VERTICAL, command=canvas.yview)
        scroll_frame = tb.Frame(canvas)

        scroll_frame.bind('<Configure>',
                          lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor=NW)
        canvas.configure(yscrollcommand=v_scroll.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        v_scroll.pack(side=RIGHT, fill=Y)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind_all('<MouseWheel>', _on_mousewheel, add='+')

        # ── Time settings section ──
        settings_frame = tb.LabelFrame(
            scroll_frame, text='⏱  时间设置',
        )
        settings_frame.pack(fill=X, padx=5, pady=5)

        # Synchronize checkbox
        self._sync_var = tk.BooleanVar(value=False)
        sync_cb = tb.Checkbutton(
            settings_frame, text='同步所有时间', variable=self._sync_var,
            bootstyle='info-outline',
            command=self._on_sync_toggle,
        )
        sync_cb.pack(anchor=W, pady=(0, 10))

        # Three time rows
        self._creation_picker = DateTimePicker(
            settings_frame, label_text='创建时间',
            dt_var=tk.StringVar(value=datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        )
        self._creation_picker.pack(fill=X, pady=3)

        self._modification_picker = DateTimePicker(
            settings_frame, label_text='修改时间',
            dt_var=tk.StringVar(value=datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        )
        self._modification_picker.pack(fill=X, pady=3)

        self._access_picker = DateTimePicker(
            settings_frame, label_text='访问时间',
            dt_var=tk.StringVar(value=datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        )
        self._access_picker.pack(fill=X, pady=3)

        # ── Apply buttons ──
        apply_frame = tb.Frame(scroll_frame)
        apply_frame.pack(fill=X, padx=5, pady=10)

        tb.Button(
            apply_frame, text='应用到选中', bootstyle='info',
            command=self._apply_to_selected, width=18,
        ).pack(side=LEFT, padx=2)

        tb.Button(
            apply_frame, text='应用到全部', bootstyle='info-outline',
            command=self._apply_to_all, width=18,
        ).pack(side=LEFT, padx=2)

        # ── Operation buttons ──
        op_frame = tb.LabelFrame(scroll_frame, text='操作')
        op_frame.pack(fill=X, padx=5, pady=5)

        preview_btn = tb.Button(
            op_frame, text='🔍  预览修改', bootstyle='secondary-outline',
            command=self._preview_changes, width=25,
        )
        preview_btn.pack(fill=X, pady=2)

        self._apply_btn = tb.Button(
            op_frame, text='✅  执行修改', bootstyle='primary',
            command=self._apply_changes, width=25,
        )
        self._apply_btn.pack(fill=X, pady=2)

        self._undo_btn = tb.Button(
            op_frame, text='↩  撤销上次', bootstyle='danger',
            command=self._undo_changes, width=25,
            state=DISABLED,
        )
        self._undo_btn.pack(fill=X, pady=2)

        # ── Profile buttons ──
        profile_frame = tb.LabelFrame(scroll_frame, text='方案管理')
        profile_frame.pack(fill=X, padx=5, pady=5)

        tb.Button(
            profile_frame, text='💾  保存时间方案', bootstyle='success-outline',
            command=self._save_profile, width=25,
        ).pack(fill=X, pady=2)

        tb.Button(
            profile_frame, text='📂  加载时间方案', bootstyle='info-outline',
            command=self._load_profile, width=25,
        ).pack(fill=X, pady=2)

    def _build_log_panel(self):
        """Build the log output panel at the bottom."""
        log_frame = tb.LabelFrame(self, text='📋  操作日志')
        log_frame.pack(fill=BOTH, padx=5, pady=(0, 5))

        self.log = LogWidget(log_frame)
        self.log.pack(fill=BOTH, expand=True, padx=2, pady=2)

        # Clear log button on the label
        # We can add it inline
        self.log.info('FolderTimeEditor 已启动。请添加文件或文件夹开始操作。')

    def _build_status_bar(self):
        """Build the status bar at the very bottom."""
        self.status_bar = StatusBar(self)
        self.status_bar.pack(fill=X, padx=5, pady=(0, 5))

    def _get_bg(self) -> str:
        """Get the current background color from the theme."""
        try:
            style = ttk.Style()
            return style.lookup('TFrame', 'background')
        except Exception:
            return '#1a1a2e'

    # ═════════════════════════════════════════════════════════════════════
    # Drag & Drop
    # ═════════════════════════════════════════════════════════════════════

    def _setup_drag_drop(self):
        """Initialize drag-drop support via tkinterdnd2 if available."""
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
            # Register the window for drag-drop
            if hasattr(self, 'drop_target_register'):
                self.drop_target_register(DND_FILES)
                self.dnd_bind('<<Drop>>', self._on_drop)
                self.path_tree.tree.drop_target_register(DND_FILES)
                self.path_tree.tree.dnd_bind('<<Drop>>', self._on_drop)
                self.log.info('拖拽支持已启用')
        except (ImportError, Exception) as e:
            self.log.info(f'拖拽支持不可用（{e}），请使用按钮添加路径')

    def _on_drop(self, event):
        """Handle file/folder drop event."""
        data = event.data
        if not data:
            return
        # tkinterdnd2 returns paths inside {braces} or as plain text
        paths = []
        # Handle both space-separated and newline-separated drops
        raw = data.strip()
        if '{' in raw:
            # Parse brace-delimited paths
            import re
            paths = re.findall(r'\{([^}]+)\}', raw)
        else:
            # Split by whitespace
            parts = raw.split()
            for p in parts:
                # Some DnD implementations use file:// protocol
                if p.startswith('file://'):
                    from urllib.parse import unquote
                    p = unquote(p[7:])
                paths.append(p)

        added = 0
        for p in paths:
            p = p.strip().strip('"').strip("'")
            if os.path.exists(p):
                self._add_single_path(p)
                added += 1

        if added > 0:
            self.log.success(f'拖拽添加了 {added} 个路径')
            self._update_count()

    # ═════════════════════════════════════════════════════════════════════
    # File/Folder Management
    # ═════════════════════════════════════════════════════════════════════

    def _add_folder(self):
        folder = filedialog.askdirectory(title='选择文件夹')
        if folder:
            self._add_single_path(folder)
            self._update_count()
            self.log.info(f'添加文件夹：{folder}')

    def _add_file(self):
        files = filedialog.askopenfilenames(
            title='选择文件',
            filetypes=[('所有文件', '*.*')],
        )
        for f in files:
            self._add_single_path(f)
        if files:
            self._update_count()
            self.log.info(f'添加了 {len(files)} 个文件')

    def _add_single_path(self, path: str):
        """Add a single path to the tree."""
        try:
            info = self.handler.get_times(path)
            item = {
                'name': info.name,
                'path': info.path,
                'creation_time': (info.creation_dt.strftime('%Y-%m-%d %H:%M:%S')
                                  if info.creation_dt else ''),
                'modification_time': (info.modification_dt.strftime('%Y-%m-%d %H:%M:%S')
                                      if info.modification_dt else ''),
                'access_time': (info.access_dt.strftime('%Y-%m-%d %H:%M:%S')
                                if info.access_dt else ''),
                'size': self._format_size(info.size),
            }
            self.path_tree.add_items([item])
        except Exception as e:
            self.log.error(f'读取失败：{path} - {e}')

    def _remove_selected(self):
        count = len(self.path_tree.get_selected())
        self.path_tree.remove_selected()
        self._update_count()
        if count > 0:
            self.log.info(f'移除了 {count} 个路径')

    def _clear_list(self):
        count = self.path_tree.item_count()
        self.path_tree.clear_all()
        self._update_count()
        if count > 0:
            self.log.info(f'清空了 {count} 个路径')

    def _select_all(self):
        self.path_tree.select_all()

    def _update_count(self):
        count = self.path_tree.item_count()
        self._count_var.set(f'共 {count} 项')

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f'{size_bytes} B'
        elif size_bytes < 1024 ** 2:
            return f'{size_bytes / 1024:.1f} KB'
        elif size_bytes < 1024 ** 3:
            return f'{size_bytes / 1024 ** 2:.1f} MB'
        else:
            return f'{size_bytes / 1024 ** 3:.2f} GB'

    # ═════════════════════════════════════════════════════════════════════
    # Time Settings
    # ═════════════════════════════════════════════════════════════════════

    def _on_sync_toggle(self):
        """When sync is enabled, copy creation time to others."""
        if self._sync_var.get():
            c_dt = self._creation_picker.get_datetime()
            if c_dt:
                self._modification_picker.set_datetime(c_dt)
                self._access_picker.set_datetime(c_dt)
            self.log.info('时间同步已启用 — 修改创建时间将自动同步到其他时间')

    def _get_time_settings(self) -> Dict[str, Any]:
        """Collect current time settings from all pickers."""
        settings = {}

        for key, picker in [('creation', self._creation_picker),
                            ('modification', self._modification_picker),
                            ('access', self._access_picker)]:
            enabled = picker.get_enabled()
            if not enabled:
                settings[key] = {'enabled': False}
                continue

            mode = picker.get_mode()
            if mode == 'absolute':
                dt = picker.get_datetime()
                if dt:
                    settings[key] = {
                        'enabled': True,
                        'mode': 'absolute',
                        'timestamp': dt.timestamp(),
                        'datetime': dt,
                    }
                else:
                    settings[key] = {'enabled': False}
            else:  # relative
                seconds = picker.get_rel_seconds()
                settings[key] = {
                    'enabled': True,
                    'mode': 'relative',
                    'seconds': seconds or 0,
                }

        return settings

    def _get_deltas_for_apply(self) -> Dict[str, Optional[tuple]]:
        """Get (value, is_absolute) tuples for each time attribute."""
        deltas = {}
        settings = self._get_time_settings()

        for key in ('creation', 'modification', 'access'):
            s = settings.get(key, {})
            if not s.get('enabled'):
                deltas[key] = None
            elif s['mode'] == 'absolute':
                deltas[key] = (s['timestamp'], True)
            else:
                deltas[key] = (s['seconds'], False)

        return deltas

    def _apply_to_selected(self):
        """Apply time settings to selected items (preview + execute flow)."""
        selected = self.path_tree.get_selected()
        if not selected:
            tb.dialogs.Messagebox.show_info(title='提示', message='请先选择要修改的项目',
                                    alert=True)
            return

        paths = [s['path'] for s in selected]
        self._do_apply(paths, scope='选中')

    def _apply_to_all(self):
        """Apply time settings to all items."""
        if self.path_tree.item_count() == 0:
            tb.dialogs.Messagebox.show_info(title='提示', message='列表为空，请先添加文件或文件夹',
                                    alert=True)
            return

        paths = self.path_tree.get_paths()
        self._do_apply(paths, scope='全部')

    def _do_apply(self, paths: List[str], scope: str):
        """Core apply logic with preview dialog."""
        deltas = self._get_deltas_for_apply()
        if not any(v is not None for v in deltas.values()):
            tb.dialogs.Messagebox.show_info(title='提示', message='请至少启用一个时间设置',
                                    alert=True)
            return

        # Build changes list from current times + deltas
        changes = self._build_changes(paths, deltas)

        dlg = PreviewDialog(self, changes)
        if dlg.result:
            self._execute_changes(changes, scope)

    def _execute_changes(self, plans, scope: str):
        """Execute the changes in a background thread."""
        self._apply_btn.configure(state=DISABLED, text='⏳  执行中...')
        self.status_bar.reset()
        self.log.info(f'开始执行修改（{scope}），共 {len(plans)} 项...')

        # Run in thread to keep UI responsive
        thread = threading.Thread(
            target=self._execute_thread,
            args=(plans,),
            daemon=True,
        )
        thread.start()

    def _execute_thread(self, plans):
        """Background thread for executing changes."""
        total = len(plans)
        succeeded = 0
        failed = 0
        last_plan_data = []

        for idx, change in enumerate(plans):
            path = change['path']
            new_times = FileTimes(
                creation_time=change.get('new_creation'),
                last_write_time=change.get('new_modification'),
                last_access_time=change.get('new_access'),
            )
            success = self.handler.set_times(path, new_times)
            if success:
                succeeded += 1
            else:
                failed += 1
                self.log.error(f'失败：{os.path.basename(path)}')

            # Update progress and stats (via thread-safe call)
            self.after(0, self._update_progress, idx + 1, total, succeeded, failed)

            # Store for undo
            if not success:
                last_plan_data.append({
                    'path': path,
                    'old_creation': change.get('old_creation'),
                    'new_creation': None,
                    'old_modification': change.get('old_modification'),
                    'new_modification': None,
                    'old_access': change.get('old_access'),
                    'new_access': None,
                })

        # Done
        self._last_plan = [{
            'path': c['path'],
            'old_creation': c.get('old_creation'),
            'new_creation': c.get('new_creation'),
            'old_modification': c.get('old_modification'),
            'new_modification': c.get('new_modification'),
            'old_access': c.get('old_access'),
            'new_access': c.get('new_access'),
        } for c in plans]

        self.after(0, self._on_execute_done, total, succeeded, failed)

    def _update_progress(self, processed, total, succeeded, failed):
        self.status_bar.set_progress(processed, total)
        self.status_bar.set_stats(processed, total, succeeded, failed)

    def _on_execute_done(self, total, succeeded, failed):
        self._apply_btn.configure(state=NORMAL, text='✅  执行修改')
        self._undo_btn.configure(state=NORMAL)
        self._undo_available = True

        if failed == 0:
            self.log.success(f'执行完成！成功修改 {succeeded}/{total} 项')
        else:
            self.log.warning(f'执行完成：成功 {succeeded}，失败 {failed}（共 {total} 项）')

        tb.dialogs.Messagebox.show_info(
            title='操作完成',
            message=f'成功：{succeeded} 项\n失败：{failed} 项\n总计：{total} 项',
        )

        # Refresh treeview data
        self._refresh_tree_times()

    def _refresh_tree_times(self):
        """Refresh displayed times in the treeview."""
        # For simplicity, just re-scan all items
        all_items = self.path_tree.get_all()
        self.path_tree.clear_all()
        for item in all_items:
            path = item.get('path', '')
            if os.path.exists(path):
                self._add_single_path(path)
        self._update_count()

    # ═════════════════════════════════════════════════════════════════════
    # Undo
    # ═════════════════════════════════════════════════════════════════════

    def _undo_changes(self):
        """Undo the last batch of changes."""
        if not self._undo_available or not self._last_plan:
            tb.dialogs.Messagebox.show_info(title='提示', message='没有可撤销的修改')
            return

        confirm = tb.dialogs.Messagebox.show_question(
            title='确认撤销',
            message=f'确定要撤销上次修改（共 {len(self._last_plan)} 项）吗？',
        )
        if not confirm:
            return

        self.log.info('开始撤销上次修改...')
        succeeded = 0
        failed = 0
        total = len(self._last_plan)

        for idx, change in enumerate(self._last_plan):
            # Reverse: set old timestamps back
            path = change['path']
            if not os.path.exists(path):
                failed += 1
                self.log.error(f'撤销失败（路径不存在）：{os.path.basename(path)}')
                continue

            new_times = FileTimes(
                creation_time=change['old_creation'],
                last_write_time=change['old_modification'],
                last_access_time=change['old_access'],
            )
            success = self.handler.set_times(path, new_times)
            if success:
                succeeded += 1
            else:
                failed += 1

            self.after(0, self._update_progress, idx + 1, total, succeeded, failed)

        self._undo_available = False
        self._undo_btn.configure(state=DISABLED)
        self._last_plan = []

        if failed == 0:
            self.log.success(f'撤销完成！恢复 {succeeded}/{total} 项')
        else:
            self.log.warning(f'撤销完成：成功 {succeeded}，失败 {failed}（共 {total} 项）')

        self._refresh_tree_times()

    # ═════════════════════════════════════════════════════════════════════
    # Profile Management
    # ═════════════════════════════════════════════════════════════════════

    def _get_current_settings_dict(self) -> Dict[str, Any]:
        """Serialize current time settings to a dict for saving."""
        settings = {}
        for key, picker in [('creation', self._creation_picker),
                            ('modification', self._modification_picker),
                            ('access', self._access_picker)]:
            settings[key] = {
                'enabled': picker.get_enabled(),
                'mode': picker.get_mode(),
            }
            if picker.get_mode() == 'absolute':
                dt = picker.get_datetime()
                if dt:
                    settings[key]['datetime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                settings[key]['days'] = picker._days_var.get()
                settings[key]['hours'] = picker._hours_var.get()
                settings[key]['minutes'] = picker._mins_var.get()

        settings['sync_enabled'] = self._sync_var.get()
        return settings

    def _save_profile(self):
        dlg = ProfileDialog(self, self._get_current_settings_dict())
        # ProfileDialog handles saving internally

    def _load_profile(self):
        dlg = ProfileDialog(self, self._get_current_settings_dict())
        if dlg.result_settings:
            settings = dlg.result_settings
            self._apply_profile_settings(settings)
            self.log.success(f'时间方案已加载')

    def _apply_profile_settings(self, settings: Dict[str, Any]):
        """Apply loaded profile settings to the pickers."""
        for key, picker in [('creation', self._creation_picker),
                            ('modification', self._modification_picker),
                            ('access', self._access_picker)]:
            s = settings.get(key, {})
            picker.set_enabled(s.get('enabled', True))

            if s.get('mode') == 'absolute' and s.get('datetime'):
                try:
                    dt = datetime.strptime(s['datetime'], '%Y-%m-%d %H:%M:%S')
                    picker.set_datetime(dt)
                except Exception:
                    pass

            # Set mode variable (Radiobutton)
            if 'mode' in s:
                picker.mode_var.set(s['mode'])
                picker._on_mode_change()

            # Set relative values
            if 'days' in s:
                picker._days_var.set(s['days'])
            if 'hours' in s:
                picker._hours_var.set(s['hours'])
            if 'minutes' in s:
                picker._mins_var.set(s['minutes'])

        if 'sync_enabled' in settings:
            self._sync_var.set(settings['sync_enabled'])

    # ═════════════════════════════════════════════════════════════════════
    # Preview
    # ═════════════════════════════════════════════════════════════════════

    def _preview_changes(self):
        """Preview changes for all items (or selected, if any)."""
        selected = self.path_tree.get_selected()
        if selected:
            paths = [s['path'] for s in selected]
            scope = '选中'
        else:
            paths = self.path_tree.get_paths()
            scope = '全部'

        if not paths:
            tb.dialogs.Messagebox.show_info(title='提示', message='列表为空，请先添加文件或文件夹',
                                    alert=True)
            return

        deltas = self._get_deltas_for_apply()
        if not any(v is not None for v in deltas.values()):
            tb.dialogs.Messagebox.show_info(title='提示', message='请至少启用一个时间设置',
                                    alert=True)
            return

        changes = self._build_changes(paths, deltas)
        PreviewDialog(self, changes, title=f'预览修改（{scope}）')
        self.log.info(f'预览完成：{len(changes)} 项将被修改')

    # ═════════════════════════════════════════════════════════════════════
    # Apply (direct)
    # ═════════════════════════════════════════════════════════════════════

    def _apply_changes(self):
        """Directly apply changes without preview (uses confirm dialog)."""
        paths = self.path_tree.get_paths()
        if not paths:
            tb.dialogs.Messagebox.show_info(title='提示', message='列表为空，请先添加文件或文件夹',
                                    alert=True)
            return

        deltas = self._get_deltas_for_apply()
        if not any(v is not None for v in deltas.values()):
            tb.dialogs.Messagebox.show_info(title='提示', message='请至少启用一个时间设置',
                                    alert=True)
            return

        confirm = tb.dialogs.Messagebox.show_question(
            title='确认执行',
            message=f'确定要对 {len(paths)} 个项目执行时间修改吗？\n\n'
                    '建议先点击"预览修改"确认变更内容。',
        )
        if not confirm:
            return

        changes = self._build_changes(paths, deltas)
        self._execute_changes(changes, '全部')

    # ═════════════════════════════════════════════════════════════════════
    # Helpers
    # ═════════════════════════════════════════════════════════════════════

    def _on_escape(self):
        """Handle Escape key."""
        pass


    def _build_changes(self, paths, deltas):
        """Build a list of change dicts from paths and time deltas.
        
        Each change dict: {path, old_creation/new_creation, old_modification/new_modification, 
                           old_access/new_access}
        """
        changes = []
        for path in paths:
            times = self.handler.get_times(path)
            if times is None:
                continue
            old_creation = times.creation_time
            old_mod = times.last_write_time
            old_access = times.last_access_time

            new_creation = old_creation
            new_mod = old_mod
            new_access = old_access

            delta_c = deltas.get('creation')
            delta_m = deltas.get('modification')
            delta_a = deltas.get('access')

            if delta_c is not None:
                val, is_abs = delta_c
                if is_abs:
                    new_creation = datetime.fromtimestamp(val)
                else:
                    new_creation = old_creation + timedelta(seconds=val) if old_creation else None

            if delta_m is not None:
                val, is_abs = delta_m
                if is_abs:
                    new_mod = datetime.fromtimestamp(val)
                else:
                    new_mod = old_mod + timedelta(seconds=val) if old_mod else None

            if delta_a is not None:
                val, is_abs = delta_a
                if is_abs:
                    new_access = datetime.fromtimestamp(val)
                else:
                    new_access = old_access + timedelta(seconds=val) if old_access else None

            changes.append({
                'path': path,
                'old_creation': old_creation,
                'new_creation': new_creation,
                'old_modification': old_mod,
                'new_modification': new_mod,
                'old_access': old_access,
                'new_access': new_access,
            })
        return changes

    def _show_about(self):
        tb.dialogs.Messagebox.show_info(
            title='关于 FolderTimeEditor',
            message=(
                'FolderTimeEditor v1.0\n'
                '文件夹/文件时间批量修改工具\n\n'
                '基于 Windows API 开发\n'
                '使用 tkinter + ttkbootstrap 构建\n\n'
                '© 2026 Nous Research'
            ),
        )
