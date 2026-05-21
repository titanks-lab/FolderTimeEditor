"""Dialog windows for FolderTimeEditor.

Provides:
  - PreviewDialog: shows planned changes before applying
  - ProfileDialog: save/load time profiles as .json files
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk
from typing import Any, Dict, List, Optional

import ttkbootstrap as tb
from ttkbootstrap.constants import *

from .widgets import DateTimePicker, PathTreeView


# ── PreviewDialog ──────────────────────────────────────────────────────────

class PreviewDialog(tb.Toplevel):
    """Modal dialog showing preview of timestamp changes.

    Displays a table with old vs new timestamps for each file/folder.
    """

    def __init__(
        self,
        master,
        changes: List[Dict[str, Any]],
        title: str = '预览修改',
    ):
        super().__init__(master)
        self.title(title)
        self.changes = changes
        self.result = False  # True if user clicks "执行"

        # Window setup
        self.transient(master)
        self.grab_set()
        self.geometry('900x500')

        # Center on parent
        self.update_idletasks()
        pw = master.winfo_width()
        ph = master.winfo_height()
        px = master.winfo_rootx()
        py = master.winfo_rooty()
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f'+{px + (pw - w) // 2}+{py + (ph - h) // 2}')

        self._build_ui()
        self._populate()

        self.wait_window()

    def _build_ui(self):
        # Info label
        info_frame = tb.Frame(self)
        info_frame.pack(fill=X, padx=10, pady=(10, 0))

        count = len(self.changes)
        tb.Label(
            info_frame,
            text=f'即将对 {count} 个文件/文件夹执行时间修改：',
            font=('Segoe UI', 11),
        ).pack(anchor=W)

        # Treeview for old/new comparison
        columns = ('name', 'attr', 'old_time', 'new_time')
        self.tree = ttk.Treeview(self, columns=columns, show='headings',
                                 height=15)
        self.tree.heading('name', text='文件/文件夹')
        self.tree.heading('attr', text='时间属性')
        self.tree.heading('old_time', text='当前时间')
        self.tree.heading('new_time', text='修改后时间')

        self.tree.column('name', width=300, minwidth=150)
        self.tree.column('attr', width=100, minwidth=80)
        self.tree.column('old_time', width=180, minwidth=120)
        self.tree.column('new_time', width=180, minwidth=120)

        v_scroll = ttk.Scrollbar(self, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scroll.set)

        self.tree.pack(side=LEFT, fill=BOTH, expand=True, padx=(10, 0), pady=10)
        v_scroll.pack(side=LEFT, fill=Y, pady=10)

        # Bottom buttons
        btn_frame = tb.Frame(self)
        btn_frame.pack(fill=X, padx=10, pady=(0, 10))

        tb.Button(btn_frame, text='取消', bootstyle='secondary',
                  command=self.destroy, width=12).pack(side=RIGHT, padx=2)
        tb.Button(btn_frame, text='执行修改', bootstyle='primary',
                  command=self._apply, width=12).pack(side=RIGHT, padx=2)

    def _populate(self):
        def fmt(ts):
            if ts is None:
                return '—'
            try:
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                return str(ts)

        for change in self.changes:
            name = os.path.basename(change.get('path', ''))
            path = change.get('path', '')
            for attr_key, attr_name in [('creation', '创建时间'),
                                         ('modification', '修改时间'),
                                         ('access', '访问时间')]:
                old_v = change.get(f'old_{attr_key}')
                new_v = change.get(f'new_{attr_key}')
                if old_v == new_v:
                    continue  # skip unchanged
                if new_v is None:
                    continue  # not being modified

                self.tree.insert('', END, values=(
                    name if attr_key == 'creation' else '',
                    attr_name,
                    fmt(old_v),
                    fmt(new_v),
                ))
                # Store path for identification
                if attr_key == 'creation':
                    self.tree.set(self.tree.get_children()[-1], 'name', name)

    def _apply(self):
        self.result = True
        self.destroy()


# ── ProfileDialog ──────────────────────────────────────────────────────────

class ProfileDialog(tb.Toplevel):
    """Dialog for managing time-setting profiles.

    Profiles are saved/loaded as .json files.
    """

    def __init__(self, master, current_settings: Dict[str, Any]):
        super().__init__(master)
        self.title('时间方案管理')
        self.current_settings = current_settings
        self.result_settings: Optional[Dict[str, Any]] = None

        self.transient(master)
        self.grab_set()
        self.geometry('550x400')
        self.resizable(True, True)
        self.minsize(450, 300)

        # Center
        self.update_idletasks()
        pw = master.winfo_width()
        ph = master.winfo_height()
        px = master.winfo_rootx()
        py = master.winfo_rooty()
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f'+{px + (pw - w) // 2}+{py + (ph - h) // 2}')

        self._profiles_dir = os.path.join(os.path.expanduser('~'), '.folder-time-editor', 'profiles')
        os.makedirs(self._profiles_dir, exist_ok=True)

        self._build_ui()
        self._refresh_list()

        self.wait_window()

    def _build_ui(self):
        # Top frame: list of profiles
        top = tb.LabelFrame(self, text='已保存的方案')
        top.pack(fill=BOTH, expand=True, padx=10, pady=(10, 5))

        self.profile_listbox = tk.Listbox(top, font=('Segoe UI', 10),
                                          selectmode=SINGLE)
        list_scroll = ttk.Scrollbar(top, orient=VERTICAL,
                                    command=self.profile_listbox.yview)
        self.profile_listbox.configure(yscrollcommand=list_scroll.set)

        self.profile_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        list_scroll.pack(side=RIGHT, fill=Y)

        self.profile_listbox.bind('<Double-Button-1>', lambda e: self._load_selected())

        # Bottom buttons
        btn_frame = tb.Frame(self)
        btn_frame.pack(fill=X, padx=10, pady=(5, 10))

        tb.Button(btn_frame, text='保存当前方案', bootstyle='success-outline',
                  command=self._save_profile, width=16).pack(side=LEFT, padx=2)
        tb.Button(btn_frame, text='加载选中方案', bootstyle='primary',
                  command=self._load_selected, width=16).pack(side=LEFT, padx=2)
        tb.Button(btn_frame, text='删除选中', bootstyle='danger-outline',
                  command=self._delete_selected, width=12).pack(side=LEFT, padx=2)

        tb.Button(btn_frame, text='关闭', bootstyle='secondary',
                  command=self.destroy, width=10).pack(side=RIGHT, padx=2)

    def _refresh_list(self):
        self.profile_listbox.delete(0, END)
        if not os.path.isdir(self._profiles_dir):
            return
        for fname in sorted(os.listdir(self._profiles_dir)):
            if fname.endswith('.json'):
                display = fname[:-5]  # remove .json
                self.profile_listbox.insert(END, display)

    def _get_profile_path(self, name: str) -> str:
        if not name.endswith('.json'):
            name += '.json'
        return os.path.join(self._profiles_dir, name)

    def _save_profile(self):
        name = tb.dialogs.Querybox.get_string('请输入方案名称：', title='保存方案')
        if not name:
            return
        path = self._get_profile_path(name)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.current_settings, f, ensure_ascii=False, indent=2)
            self._refresh_list()
            # Select the newly saved profile
            items = self.profile_listbox.get(0, END)
            for idx, item in enumerate(items):
                if item == name:
                    self.profile_listbox.selection_set(idx)
                    break
        except Exception as e:
            tb.dialogs.Messagebox.show_error(title='保存失败',
                                  message=f'无法保存方案：{e}')

    def _load_selected(self):
        sel = self.profile_listbox.curselection()
        if not sel:
            tb.dialogs.Messagebox.show_info(title='提示', message='请先选择一个方案',
                                    alert=True)
            return
        name = self.profile_listbox.get(sel[0])
        path = self._get_profile_path(name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.result_settings = json.load(f)
            self.destroy()
        except Exception as e:
            tb.dialogs.Messagebox.show_error(title='加载失败',
                                  message=f'无法加载方案：{e}')

    def _delete_selected(self):
        sel = self.profile_listbox.curselection()
        if not sel:
            return
        name = self.profile_listbox.get(sel[0])
        confirm = tb.dialogs.Messagebox.show_question(
            title='确认删除',
            message=f'确定要删除方案 "{name}" 吗？',
        )
        if confirm:
            path = self._get_profile_path(name)
            try:
                os.remove(path)
                self._refresh_list()
            except Exception as e:
                tb.dialogs.Messagebox.show_error(title='删除失败',
                                      message=f'无法删除方案：{e}')
