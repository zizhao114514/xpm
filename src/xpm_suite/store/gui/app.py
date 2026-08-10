"""
X-Store GUI - 图形界面主窗口
深色主题 + 卡片瀑布流 + 侧边栏分类 + 下载队列面板

设计理念: 美观大方，专业但不沉闷
主题色: 深蓝底 + 珊瑚红强调 + 金色星星
"""

import os, sys, threading, time
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    HAS_TK = True
except ImportError:
    HAS_TK = False

from ...store import (
    get_categories, get_apps_by_category, get_top_apps,
    search_apps, get_app_detail, rate_app, get_rating,
    add_custom, remove_custom,
)
from ...store.gui.store_gui import (
    StoreState, get_state, format_stars, format_popularity_bar,
    get_app_icon, get_format_badge, ProgressTracker,
)
from ...store.gui.theme import get_theme, list_themes, lighten, darken
from ...core.statusdb import get_db

# PAM / auth 延迟导入（避免无 tkinter 环境时报错）
def _lazy_auth():
    from ...core.auth import verify_action, AuthAction
    return verify_action, AuthAction

# === 常量 ===

WINDOW_TITLE = "X-Store - 应用商店"
WINDOW_W = 1100
WINDOW_H = 720
SIDEBAR_W = 200
CARD_W = 280
CARD_H = 160
CARD_GAP = 14
TOPBAR_H = 56

# === 主窗口 ===

class XStoreApp:
    """X-Store 主窗口"""

    def __init__(self, root: "tk.Tk"):
        self.root = root
        self.state = get_state()
        self.tracker = ProgressTracker()
        self._cards = []  # 当前卡片引用
        self._init_window()
        self._init_styles()
        self._build_layout()
        self._refresh_all()
        # 订阅状态变化
        self.state.subscribe(self._refresh_all)
        self.tracker.subscribe(self._refresh_downloads)

        # 后台检查更新
        threading.Thread(target=self._check_for_updates, daemon=True).start()

    def _init_window(self):
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.minsize(900, 600)
        try:
            self.root.iconname("xstore")
        except:
            pass

    def _init_styles(self):
        self.style = ttk.Style()
        theme = self.state.theme
        self.bg = theme["bg"]
        self.bg_card = theme["bg_card"]
        self.bg_sidebar = theme["bg_sidebar"]
        self.text = theme["text"]
        self.text_dim = theme["text_dim"]
        self.accent = theme["accent"]
        self.accent2 = theme["accent2"]
        self.success = theme["success"]
        self.warning = theme["warning"]
        self.danger = theme["danger"]
        self.info = theme["info"]
        self.border = theme["border"]
        self.radius = theme["radius"]
        self.font_main = theme["font_main"]
        self.font_mono = theme["font_mono"]

        self.root.configure(bg=self.bg)
        self.style.theme_use("clam")

        # 通用样式
        self.style.configure("TFrame", background=self.bg)
        self.style.configure("Card.TFrame",
                           background=self.bg_card,
                           relief="flat", borderwidth=0)
        self.style.configure("Sidebar.TFrame",
                           background=self.bg_sidebar)
        self.style.configure("TLabel", background=self.bg,
                           foreground=self.text,
                           font=(self.font_main, 11))
        self.style.configure("CardTitle.TLabel",
                           background=self.bg_card,
                           foreground=self.text,
                           font=(self.font_main, 13, "bold"))
        self.style.configure("CardDesc.TLabel",
                           background=self.bg_card,
                           foreground=self.text_dim,
                           font=(self.font_main, 10))
        self.style.configure("Sidebar.TLabel",
                           background=self.bg_sidebar,
                           foreground=self.text,
                           font=(self.font_main, 12))
        self.style.configure("SidebarActive.TLabel",
                           background=self.accent,
                           foreground=theme["text_on_accent"],
                           font=(self.font_main, 12, "bold"))
        self.style.configure("TButton",
                           background=self.accent,
                           foreground=theme["text_on_accent"],
                           font=(self.font_main, 11),
                           borderwidth=0, relief="flat")
        self.style.map("TButton",
                      background=[("active", lighten(self.accent, 0.1)),
                                  ("pressed", darken(self.accent, 0.1))])
        self.style.configure("CardBtn.TButton",
                           background=self.accent,
                           foreground=theme["text_on_accent"],
                           font=(self.font_main, 10, "bold"),
                           borderwidth=0, relief="flat")
        self.style.map("CardBtn.TButton",
                      background=[("active", lighten(self.accent, 0.15))])
        self.style.configure("InstalledBtn.TButton",
                           background=self.success,
                           foreground="white",
                           font=(self.font_main, 10, "bold"))
        self.style.configure("TEntry",
                           fieldbackground=theme["bg_input"],
                           foreground=self.text,
                           font=(self.font_main, 11),
                           borderwidth=0)
        self.style.configure("TPanedwindow", background=self.bg)
        self.style.configure("TScrollbar",
                           background=theme["scrollbar"],
                           troughcolor=self.bg,
                           borderwidth=0)
        self.style.configure("TProgressbar",
                           background=self.accent,
                           troughcolor=theme["progress_bg"],
                           borderwidth=0)

    def _build_layout(self):
        """构建界面布局"""
        # --- 顶栏 ---
        self.topbar = tk.Frame(self.root, height=TOPBAR_H,
                              bg=self.bg_sidebar)
        self.topbar.pack(side="top", fill="x")
        self.topbar.pack_propagate(False)

        # Logo
        tk.Label(self.topbar, text="🏪 X-Store",
                bg=self.bg_sidebar, fg=self.text,
                font=(self.font_main, 16, "bold")).pack(
            side="left", padx=16, pady=12)

        # 搜索框
        search_frame = tk.Frame(self.topbar, bg=self.bg_sidebar)
        search_frame.pack(side="left", padx=20, fill="x", expand=True)
        tk.Label(search_frame, text="🔍", bg=self.bg_sidebar,
                fg=self.text_dim, font=(self.font_main, 12)).pack(
            side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        self.search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=self.state.theme["bg_input"],
            fg=self.text, insertbackground=self.text,
            font=(self.font_main, 12), relief="flat",
            highlightthickness=1,
            highlightcolor=self.accent,
            highlightbackground=self.border,
        )
        self.search_entry.pack(side="left", fill="x", expand=True,
                              ipady=4, ipadx=8)
        self.search_entry.insert(0, "搜索应用...")
        self.search_entry.bind("<FocusIn>", self._clear_search_placeholder)
        self.search_entry.bind("<FocusOut>", self._restore_search_placeholder)

        # 右侧按钮
        btn_frame = tk.Frame(self.topbar, bg=self.bg_sidebar)
        btn_frame.pack(side="right", padx=12)

        self.theme_btn = tk.Button(
            btn_frame, text="🎨", command=self._cycle_theme,
            bg=self.bg_sidebar, fg=self.text,
            font=(self.font_main, 14), relief="flat", padx=8,
            activebackground=lighten(self.bg_sidebar, 0.1))
        self.theme_btn.pack(side="left", padx=2)

        self.installed_btn = tk.Button(
            btn_frame, text="✅ 已装", command=self._toggle_installed,
            bg=self.bg_sidebar, fg=self.text,
            font=(self.font_main, 11), relief="flat", padx=8,
            activebackground=lighten(self.bg_sidebar, 0.1))
        self.installed_btn.pack(side="left", padx=2)

        self.top_btn = tk.Button(
            btn_frame, text="🔥 TOP", command=self._show_top,
            bg=self.bg_sidebar, fg=self.text,
            font=(self.font_main, 11), relief="flat", padx=8,
            activebackground=lighten(self.bg_sidebar, 0.1))
        self.top_btn.pack(side="left", padx=2)

        # --- 主体：侧边栏 + 内容区 ---
        self.main = tk.Frame(self.root, bg=self.bg)
        self.main.pack(side="top", fill="both", expand=True)

        # 侧边栏
        self.sidebar = tk.Frame(self.main, width=SIDEBAR_W,
                               bg=self.bg_sidebar)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="  分类", bg=self.bg_sidebar,
                fg=self.text_dim, font=(self.font_main, 10),
                anchor="w").pack(fill="x", padx=10, pady=(14, 6))

        self.sidebar_buttons = {}
        for cat in self.state.get_categories():
            btn = tk.Label(
                self.sidebar, text=f"  {cat['icon']}  {cat['label']}",
                bg=self.bg_sidebar, fg=self.text,
                font=(self.font_main, 12), anchor="w",
                cursor="hand2")
            btn.pack(fill="x", padx=4, pady=2, ipady=6)
            btn.bind("<Button-1>", lambda e, k=cat['key']: self._select_category(k))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=lighten(self.bg_sidebar, 0.08)))
            btn.bind("<Leave>", lambda e, b=btn: b.config(
                bg=self.accent if b._cat_key == self.state.current_category else self.bg_sidebar))
            btn._cat_key = cat['key']
            self.sidebar_buttons[cat['key']] = btn

        # 分割线
        tk.Frame(self.sidebar, height=1, bg=self.border).pack(
            fill="x", padx=10, pady=8)

        # 底部: 主题名
        self.theme_label = tk.Label(
            self.sidebar, text=f"🎨 {self.state.theme['name']}",
            bg=self.bg_sidebar, fg=self.text_dim,
            font=(self.font_main, 9))
        self.theme_label.pack(side="bottom", fill="x", padx=10, pady=8)

        # 版本 + 更新提示
        from ....core.self_update import check_update
        update_info = check_update()
        ver_text = f"v{update_info.get('current', '3.1.0')} Suite"
        if update_info.get("update_available"):
            ver_text += " 🟢有更新"
        tk.Label(self.sidebar, text=ver_text, bg=self.bg_sidebar,
                fg=self.text_dim, font=(self.font_main, 9)).pack(
            side="bottom", fill="x", padx=10)

        # --- 内容区（带滚动）---
        self.canvas_frame = tk.Frame(self.main, bg=self.bg)
        self.canvas_frame.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg=self.bg,
                                highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.canvas_frame,
                                      orient="vertical",
                                      command=self.canvas.yview,
                                      bg=self.state.theme["scrollbar"])
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.cards_frame = tk.Frame(self.canvas, bg=self.bg)
        self.canvas_window = self.canvas.create_window(
            0, 0, window=self.cards_frame, anchor="nw")

        self.cards_frame.bind("<Configure>", self._on_cards_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # --- 底部下载队列 ---
        self.bottom_bar = tk.Frame(self.root, height=36, bg=self.bg_sidebar)
        self.bottom_bar.pack(side="bottom", fill="x")
        self.bottom_bar.pack_propagate(False)

        self.status_label = tk.Label(
            self.bottom_bar, text="就绪", bg=self.bg_sidebar,
            fg=self.text_dim, font=(self.font_main, 10), anchor="w")
        self.status_label.pack(side="left", padx=12)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.bottom_bar, variable=self.progress_var,
            maximum=100, length=200, mode="determinate")
        self.progress_bar.pack(side="right", padx=12)

    # === 事件处理 ===

    def _on_cards_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width - 4)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _clear_search_placeholder(self, event):
        if self.search_entry.get() == "搜索应用...":
            self.search_entry.delete(0, "end")

    def _restore_search_placeholder(self, event):
        if not self.search_entry.get():
            self.search_entry.insert(0, "搜索应用...")

    def _on_search(self, *args):
        q = self.search_var.get().strip()
        if q and q != "搜索应用...":
            self.state.set_search(q)
        elif not q:
            self.state.set_search("")
            self._refresh_all()

    def _select_category(self, key: str):
        self.state.set_category(key)
        self.search_var.set("")
        self._highlight_sidebar()

    def _show_top(self):
        self.state.current_category = "__top__"
        self.state.search_query = ""
        self.search_var.set("")
        self._highlight_sidebar()
        self._refresh_all()

    def _toggle_installed(self):
        self.state.toggle_installed_filter()
        self._refresh_all()

    def _cycle_theme(self):
        self.state.cycle_theme()
        self._init_styles()
        self._rebuild_ui_colors()
        self.theme_label.config(text=f"🎨 {self.state.theme['name']}")

    def _highlight_sidebar(self):
        for k, btn in self.sidebar_buttons.items():
            if k == self.state.current_category:
                btn.config(bg=self.accent, fg=self.state.theme["text_on_accent"])
            else:
                btn.config(bg=self.bg_sidebar, fg=self.text)

    def _rebuild_ui_colors(self):
        """换主题后刷新颜色"""
        t = self.state.theme
        self.root.configure(bg=t["bg"])
        self.topbar.config(bg=t["bg_sidebar"])
        self.sidebar.config(bg=t["bg_sidebar"])
        self.main.config(bg=t["bg"])
        self.canvas.config(bg=t["bg"])
        self.cards_frame.config(bg=t["bg"])
        self.bottom_bar.config(bg=t["bg_sidebar"])
        self._highlight_sidebar()
        self._refresh_all()

    # === 刷新 ===

    def _refresh_all(self):
        """刷新所有卡片"""
        self._clear_cards()
        apps = self.state.get_visible_apps()

        if not apps:
            self._show_empty_state()
            return

        cols = max(1, (self.canvas.winfo_width() - 20) // (CARD_W + CARD_GAP))
        if cols < 1: cols = 1

        for i, app in enumerate(apps):
            row = i // cols
            col = i % cols
            card = self._create_card(self.cards_frame, app)
            card.grid(row=row, column=col, padx=CARD_GAP//2, pady=CARD_GAP//2,
                      sticky="nsew")
            self._cards.append(card)

        # 配置列权重
        for c in range(cols):
            self.cards_frame.grid_columnconfigure(c, weight=1, minsize=CARD_W)

        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _clear_cards(self):
        for c in self._cards:
            c.destroy()
        self._cards.clear()

    def _show_empty_state(self):
        tk.Label(self.cards_frame, text="🔍 没有找到匹配的应用",
                bg=self.bg, fg=self.text_dim,
                font=(self.font_main, 14)).pack(pady=40)

    def _create_card(self, parent, app: dict) -> "tk.Frame":
        """创建单个应用卡片"""
        theme = self.state.theme
        card = tk.Frame(parent, bg=theme["bg_card"],
                       highlightbackground=theme["border"],
                       highlightthickness=1)
        card.configure(width=CARD_W, height=CARD_H)

        # 圆角模拟（用内边距实现）
        inner = tk.Frame(card, bg=theme["bg_card"])
        inner.pack(fill="both", expand=True, padx=10, pady=8)

        # 图标 + 名称 + 徽章
        top = tk.Frame(inner, bg=theme["bg_card"])
        top.pack(fill="x")

        icon = get_app_icon(app.get("name", ""))
        tk.Label(top, text=icon, bg=theme["bg_card"],
                font=(self.font_main, 20)).pack(side="left")

        name_frame = tk.Frame(top, bg=theme["bg_card"])
        name_frame.pack(side="left", padx=8, fill="x", expand=True)

        display = app.get("display", app.get("name", "?"))
        tk.Label(name_frame, text=display[:18],
                bg=theme["bg_card"], fg=theme["text"],
                font=(self.font_main, 12, "bold"),
                anchor="w").pack(fill="x")

        # 格式徽章
        fmt = app.get("source_format", "deb")
        badge_color = theme["badge_oil"] if fmt == "oil" else theme["badge_deb"]
        badge_text = ".oil" if fmt == "oil" else ".deb"
        tk.Label(top, text=badge_text, bg=badge_color,
                fg="white", font=(self.font_main, 8, "bold"),
                padx=4, pady=0).pack(side="right", padx=2)

        # 描述
        desc = app.get("desc", "")[:52]
        tk.Label(inner, text=desc, bg=theme["bg_card"],
                fg=theme["text_dim"],
                font=(self.font_main, 9), anchor="w",
                wraplength=CARD_W - 24, justify="left").pack(
            fill="x", pady=(4, 2), anchor="w")

        # 星星评分
        rating = get_rating(app.get("name", ""))
        avg = rating.get("avg", 0)
        cnt = rating.get("count", 0)
        star_frame = tk.Frame(inner, bg=theme["bg_card"])
        star_frame.pack(fill="x", pady=2)
        star_text = format_stars(avg, cnt) if cnt > 0 else "☆☆☆☆☆ 未评分"
        tk.Label(star_frame, text=star_text,
                bg=theme["bg_card"], fg=theme["star"],
                font=(self.font_main, 9)).pack(side="left")

        # 流行度条
        pop = app.get("popularity", 0)
        bar_frame = tk.Frame(inner, bg=theme["bg_card"])
        bar_frame.pack(fill="x", pady=(2, 4))
        bar_w = int((CARD_W - 24) * pop / 100)
        bar_canvas = tk.Canvas(bar_frame, height=4, bg=theme["progress_bg"],
                              highlightthickness=0)
        bar_canvas.pack(fill="x")
        bar_canvas.create_rectangle(0, 0, bar_w, 4, fill=theme["accent"], outline="")

        # 底部: 安装状态 + 按钮
        bottom = tk.Frame(inner, bg=theme["bg_card"])
        bottom.pack(fill="x", side="bottom")

        is_inst = self.state.is_installed(app.get("name", ""))
        if is_inst:
            tk.Label(bottom, text="✅ 已安装",
                    bg=theme["bg_card"], fg=theme["success"],
                    font=(self.font_main, 9, "bold")).pack(side="left")
        else:
            tk.Label(bottom, text="⭐ 可安装",
                    bg=theme["bg_card"], fg=theme["text_dim"],
                    font=(self.font_main, 9)).pack(side="left")

        btn_text = "卸载" if is_inst else "安装"
        btn_cmd = lambda n=app.get("name", ""): self._install_or_remove(n, is_inst)
        btn_style = "InstalledBtn.TButton" if is_inst else "CardBtn.TButton"
        btn = ttk.Button(bottom, text=btn_text, command=btn_cmd, style=btn_style)
        btn.pack(side="right")

        # 点击卡片打开详情
        card.bind("<Button-1>", lambda e, n=app.get("name",""): self._show_detail(n))
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e, n=app.get("name",""): self._show_detail(n))

        return card

    # === 操作 ===

    def _install_or_remove(self, name: str, is_installed: bool):
        if is_installed:
            if messagebox.askyesno("确认卸载", f"确定要卸载 {name} 吗？"):
                # 检查权限
                if os.geteuid() != 0:
                    messagebox.showwarning(
                        "需要权限",
                        f"卸载 {name} 需要管理员权限。\n\n"
                        f"请通过 sudo/gksu 重新启动 X-Store GUI:\n"
                        f"  sudo xstore-gui\n或\n  gksu xstore-gui"
                    )
                    return
                threading.Thread(target=self._do_remove, args=(name,), daemon=True).start()
        else:
            # 安装需要认证
            if os.geteuid() != 0:
                messagebox.showwarning(
                    "需要权限",
                    f"安装 {name} 需要管理员权限。\n\n"
                    f"请通过 sudo/gksu 重新启动 X-Store GUI:\n"
                    f"  sudo xstore-gui\n或\n  gksu xstore-gui"
                )
                return
            threading.Thread(target=self._do_install, args=(name,), daemon=True).start()

    def _do_install(self, name: str):
        self.status_label.config(text=f"⏳ 正在安装 {name}...")
        def progress(current, total, info):
            if current < 0:
                self.status_label.config(text=f"❌ {info}")
                return
            pct = int(current / max(total, 1) * 100)
            self.progress_var.set(pct)
            self.status_label.config(text=f"⏳ {name} {pct}% - {info}")
        ok = self.state.install_app(name, progress)
        if ok:
            self.status_label.config(text=f"✅ {name} 安装完成")
            self.progress_var.set(100)
        else:
            self.status_label.config(text=f"❌ {name} 安装失败")
        self.root.after(2000, lambda: self.progress_var.set(0))
        self.root.after(2000, lambda: self.status_label.config(text="就绪"))

    def _do_remove(self, name: str):
        self.state.remove_app(name)
        self.status_label.config(text=f"🗑️ {name} 已卸载")
        self.root.after(2000, lambda: self.status_label.config(text="就绪"))

    def _show_detail(self, name: str):
        """弹出详情窗口"""
        detail = self.state.get_app_detail(name)
        if not detail:
            return

        win = tk.Toplevel(self.root)
        win.title(detail.get("display", name))
        win.geometry("520x600")
        win.configure(bg=self.bg)
        win.transient(self.root)

        theme = self.state.theme
        # 图标 + 名称
        header = tk.Frame(win, bg=theme["bg_card"], padx=16, pady=12)
        header.pack(fill="x")
        tk.Label(header, text=get_app_icon(name), bg=theme["bg_card"],
                font=(self.font_main, 28)).pack(side="left")
        tk.Label(header, text=detail.get("display", name),
                bg=theme["bg_card"], fg=theme["text"],
                font=(self.font_main, 16, "bold")).pack(side="left", padx=10)

        # 评分
        rating = detail.get("rating_avg", 0)
        cnt = detail.get("rating_count", 0)
        star_text = format_stars(rating, cnt) if cnt > 0 else "☆☆☆☆☆ 未评分"
        tk.Label(win, text=star_text, bg=self.bg, fg=theme["star"],
                font=(self.font_main, 12)).pack(anchor="w", padx=16, pady=4)

        # 描述
        tk.Label(win, text=detail.get("desc", ""),
                bg=self.bg, fg=theme["text"],
                font=(self.font_main, 11), wraplength=480,
                justify="left", anchor="w").pack(
            fill="x", padx=16, pady=8, anchor="w")

        # 信息表格
        info_frame = tk.Frame(win, bg=self.bg)
        info_frame.pack(fill="x", padx=16, pady=4)

        rows = [
            ("分类", detail.get("category", "")),
            ("格式", detail.get("source_format", "deb")),
            ("主页", detail.get("homepage", "—")),
        ]
        deps = detail.get("deps", detail.get("packages", []))
        if deps:
            rows.append(("依赖", ", ".join(deps[:5])))

        for label, val in rows:
            r = tk.Frame(info_frame, bg=self.bg)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=f"{label}:", bg=self.bg,
                    fg=theme["text_dim"],
                    font=(self.font_main, 10, "bold"),
                    width=8, anchor="e").pack(side="left", padx=(0, 8))
            tk.Label(r, text=str(val)[:60], bg=self.bg,
                    fg=theme["text"],
                    font=(self.font_main, 10), anchor="w").pack(side="left")

        # 评分区
        rate_frame = tk.LabelFrame(win, text="  评分  ", bg=self.bg,
                                   fg=theme["text_dim"],
                                   font=(self.font_main, 10))
        rate_frame.pack(fill="x", padx=16, pady=12)

        btn_row = tk.Frame(rate_frame, bg=self.bg)
        btn_row.pack(pady=6)
        for i in range(1, 6):
            star_btn = tk.Button(
                btn_row, text="★" * i + "☆" * (5 - i),
                command=lambda s=i: self._submit_rating(name, s, win),
                bg=self.bg, fg=theme["star"],
                font=(self.font_main, 12), relief="flat",
                padx=6, activebackground=self.bg)
            star_btn.pack(side="left", padx=2)

        # 评论输入
        self.comment_var = tk.StringVar()
        tk.Entry(rate_frame, textvariable=self.comment_var,
                bg=theme["bg_input"], fg=theme["text"],
                font=(self.font_main, 10), relief="flat").pack(
            fill="x", padx=8, pady=4, ipady=3)
        self._rating_name = name

        # 最近评论
        ratings = detail.get("ratings", [])
        if ratings:
            tk.Label(win, text="最近评论:", bg=self.bg,
                    fg=theme["text_dim"],
                    font=(self.font_main, 10, "bold")).pack(
                anchor="w", padx=16, pady=(8, 2))
            for r in ratings[-3:]:
                rtext = f"  ★{r.get('stars','?')} {r.get('comment','')[:50]}"
                tk.Label(win, text=rtext, bg=self.bg,
                        fg=theme["text_dim"],
                        font=(self.font_main, 9)).pack(
                    anchor="w", padx=16)

        # 底部按钮
        btn_frame = tk.Frame(win, bg=self.bg)
        btn_frame.pack(side="bottom", fill="x", padx=16, pady=12)

        is_inst = self.state.is_installed(name)
        if is_inst:
            ttk.Button(btn_frame, text="卸载", style="InstalledBtn.TButton",
                       command=lambda: [
                           self._check_root_and_run(name, "remove", win)
                       ]).pack(
                side="right", padx=4)
        else:
            ttk.Button(btn_frame, text="安装", style="CardBtn.TButton",
                       command=lambda: [
                           self._check_root_and_run(name, "install", win)
                       ]).pack(
                side="right", padx=4)

    def _check_root_and_run(self, name: str, action: str, win: "tk.Toplevel"):
        """检查 root 权限 + PAM 认证后执行安装/卸载"""
        if os.geteuid() != 0:
            messagebox.showwarning(
                "需要管理员权限",
                f"{'安装' if action == 'install' else '卸载'} {name} "
                f"需要管理员权限。\n\n请通过以下方式重新启动:\n"
                f"  sudo xstore-gui\n或\n  gksu xstore-gui",
                parent=win,
            )
            win.destroy()
            return

        # PAM 认证（GUI 已 root，但若通过 sudo/gksu/pkexec 提权则自动放行；
        # 若是直接 root 登录，会要求密码验证）
        _verify_action, _AuthAction = _lazy_auth()
        auth_action = _AuthAction.INSTALL if action == "install" else _AuthAction.REMOVE
        ok, msg = _verify_action(auth_action, name)
        if not ok:
            messagebox.showerror(
                "认证失败",
                f"🔐 PAM 认证未通过: {msg}\n\n"
                f"无法{'安装' if action == 'install' else '卸载'} {name}",
                parent=win,
            )
            win.destroy()
            return

        if action == "install":
            threading.Thread(target=self._do_install, args=(name,), daemon=True).start()
        else:
            self._do_remove(name)
        win.destroy()

    def _check_for_updates(self):
        """后台检查更新"""
        try:
            from ....core.self_update import check_update
            info = check_update()
            if info.get("update_available"):
                self.root.after(0, lambda: messagebox.showinfo(
                    "发现更新",
                    f"XPM Suite 有新版本!\n\n"
                    f"当前: v{info['current']}\n"
                    f"最新: v{info['latest']}\n\n"
                    f"请在终端运行:\n  xpm self-update"
                ))
        except Exception:
            pass

    def _submit_rating(self, name: str, stars: int, win: "tk.Toplevel"):
        comment = self.comment_var.get().strip()
        self.state.rate_app(name, stars, comment)
        messagebox.showinfo("感谢!", f"已提交 {stars} 星评分")
        win.destroy()
        self._refresh_all()

    def _refresh_downloads(self):
        """刷新下载队列面板"""
        pass  # 简化版：进度已通过 status_label 显示

# === 启动 ===

def run_gui():
    """启动 X-Store GUI"""
    if not HAS_TK:
        print("❌ 当前环境没有 tkinter，无法启动 GUI")
        print("  在 Debian/Ubuntu 上安装: apt install python3-tk")
        return 1

    # 1. 检查 root 权限
    if os.geteuid() != 0:
        print("🔐 X-Store GUI 需要管理员权限")
        print("  请通过以下方式启动:")
        print("    sudo xstore-gui")
        print("    gksu xstore-gui")
        print("    pkexec xstore-gui")
        return 1

    # 2. PAM 认证（防止脚本自动调用 GUI 搞破坏）
    _verify_action, _AuthAction = _lazy_auth()
    ok, msg = _verify_action(_AuthAction.UPDATE, "X-Store GUI 启动")
    if not ok:
        print(f"❌ PAM 认证失败: {msg}")
        print("  GUI 已拒绝启动")
        return 1

    print(f"✅ 认证通过 ({msg})，启动 X-Store GUI...")

    # 3. 启动 GUI
    root = tk.Tk()
    app = XStoreApp(root)

    # 4. 后台检查更新（每天一次，由 self_update 内部缓存控制）
    threading.Thread(target=app._check_for_updates, daemon=True).start()

    root.mainloop()
    return 0

if __name__ == "__main__":
    sys.exit(run_gui())
