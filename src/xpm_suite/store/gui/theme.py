"""
X-Store GUI 主题系统
深色为主，浅色可选，OLED 省电模式
"""

from typing import List, Tuple

# === 主题定义 ===

THEMES = {
    "dark": {
        "name": "深色主题",
        "bg":          "#1a1a2e",   # 主背景
        "bg_card":     "#16213e",   # 卡片背景
        "bg_sidebar":  "#0f3460",   # 侧边栏
        "bg_input":    "#1e2a4a",   # 输入框
        "bg_hover":    "#1e3a5f",   # 悬停
        "bg_selected": "#e94560",   # 选中高亮
        "text":        "#eaeaea",   # 主文字
        "text_dim":    "#8899aa",   # 次要文字
        "text_on_accent": "#ffffff", # 高亮上文字
        "accent":      "#e94560",   # 强调色（红）
        "accent2":     "#533483",   # 次强调（紫）
        "success":     "#4caf50",   # 成功绿
        "warning":     "#ff9800",   # 警告橙
        "danger":      "#f44336",   # 危险红
        "info":        "#2196f3",   # 信息蓝
        "border":      "#2a3a5a",   # 边框
        "scrollbar":   "#3a4a6a",   # 滚动条
        "star":        "#ffc107",   # 星星
        "star_empty":  "#4a4a5a",   # 空星
        "badge_deb":   "#2196f3",   # .deb 徽章
        "badge_oil":   "#9c27b0",   # .oil 徽章
        "badge_installed": "#4caf50",# 已安装徽章
        "progress_bg": "#2a3a5a",   # 进度条背景
        "progress_fill":"#e94560",  # 进度条填充
        "shadow":      "#00000022",  # 阴影
        "radius":      12,           # 圆角
        "font_main":   "WenQuanYi Micro Hei",
        "font_mono":   "DejaVu Sans Mono",
    },

    "light": {
        "name": "浅色主题",
        "bg":          "#f5f5f5",
        "bg_card":     "#ffffff",
        "bg_sidebar":  "#e8e8e8",
        "bg_input":    "#eeeeee",
        "bg_hover":    "#e0e0e0",
        "bg_selected": "#1976d2",
        "text":        "#212121",
        "text_dim":    "#666666",
        "text_on_accent": "#ffffff",
        "accent":      "#1976d2",
        "accent2":     "#7b1fa2",
        "success":     "#388e3c",
        "warning":     "#f57c00",
        "danger":      "#d32f2f",
        "info":        "#1976d2",
        "border":      "#dddddd",
        "scrollbar":   "#bbbbbb",
        "star":        "#ffa000",
        "star_empty":  "#cccccc",
        "badge_deb":   "#1976d2",
        "badge_oil":   "#7b1fa2",
        "badge_installed": "#388e3c",
        "progress_bg": "#e0e0e0",
        "progress_fill":"#1976d2",
        "shadow":      "#00000011",
        "radius":      12,
        "font_main":   "WenQuanYi Micro Hei",
        "font_mono":   "DejaVu Sans Mono",
    },

    "oled": {
        "name": "OLED 纯黑（省电）",
        "bg":          "#000000",
        "bg_card":     "#0a0a0a",
        "bg_sidebar":  "#050505",
        "bg_input":    "#111111",
        "bg_hover":    "#1a1a1a",
        "bg_selected": "#bb86fc",
        "text":        "#e0e0e0",
        "text_dim":    "#666666",
        "text_on_accent": "#000000",
        "accent":      "#bb86fc",
        "accent2":     "#03dac6",
        "success":     "#4caf50",
        "warning":     "#ff9800",
        "danger":      "#cf6679",
        "info":        "#03dac6",
        "border":      "#1a1a1a",
        "scrollbar":   "#2a2a2a",
        "star":        "#ffb300",
        "star_empty":  "#333333",
        "badge_deb":   "#03dac6",
        "badge_oil":   "#bb86fc",
        "badge_installed": "#4caf50",
        "progress_bg": "#1a1a1a",
        "progress_fill":"#bb86fc",
        "shadow":      "#00000000",
        "radius":      8,
        "font_main":   "WenQuanYi Micro Hei",
        "font_mono":   "DejaVu Sans Mono",
    },

    "solarized": {
        "name": "Solarized",
        "bg":          "#002b36",
        "bg_card":     "#073642",
        "bg_sidebar":  "#00212b",
        "bg_input":    "#073642",
        "bg_hover":    "#0a4a56",
        "bg_selected": "#cb4b16",
        "text":        "#eee8d5",
        "text_dim":    "#839496",
        "text_on_accent": "#fdf6e3",
        "accent":      "#cb4b16",
        "accent2":     "#6c71c4",
        "success":     "#859900",
        "warning":     "#b58900",
        "danger":      "#dc322f",
        "info":        "#268bd2",
        "border":      "#073642",
        "scrollbar":   "#586e75",
        "star":        "#b58900",
        "star_empty":  "#586e75",
        "badge_deb":   "#268bd2",
        "badge_oil":   "#6c71c4",
        "badge_installed": "#859900",
        "progress_bg": "#073642",
        "progress_fill":"#cb4b16",
        "shadow":      "#00000033",
        "radius":      6,
        "font_main":   "WenQuanYi Micro Hei",
        "font_mono":   "DejaVu Sans Mono",
    },
}

DEFAULT_THEME = "dark"

def get_theme(name: str = DEFAULT_THEME) -> dict:
    return THEMES.get(name, THEMES[DEFAULT_THEME]).copy()

def list_themes():
    return list(THEMES.keys())

# === 工具函数 ===

def hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"

def lighten(hex_color: str, factor: float = 0.1) -> str:
    r, g, b = hex_to_rgb(hex_color)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return rgb_to_hex(r, g, b)

def darken(hex_color: str, factor: float = 0.1) -> str:
    r, g, b = hex_to_rgb(hex_color)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return rgb_to_hex(r, g, b)

def alpha_blend(hex_color: str, alpha: float) -> str:
    """将颜色与背景混合模拟透明度"""
    r, g, b = hex_to_rgb(hex_color)
    bg_r, bg_g, bg_b = 26, 26, 46  # dark bg
    r = int(r * alpha + bg_r * (1 - alpha))
    g = int(g * alpha + bg_g * (1 - alpha))
    b = int(b * alpha + bg_b * (1 - alpha))
    return rgb_to_hex(r, g, b)

if __name__ == "__main__":
    print("=== X-Store GUI 主题 ===\n")
    for key, t in THEMES.items():
        print(f"  🎨 {t['name']:<20} ({key})")
        print(f"     背景: {t['bg']}  卡片: {t['bg_card']}  强调: {t['accent']}")
    print(f"\n当前默认: {DEFAULT_THEME}")
