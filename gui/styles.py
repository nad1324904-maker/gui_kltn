"""
styles.py - Cấu hình giao diện chuẩn công nghiệp
"""

import customtkinter as ctk

# ==================== CẤU HÌNH CHUNG ====================
ctk.set_appearance_mode("dark") # hoặc "dark"
ctk.set_default_color_theme("blue")

# ==================== MÀU SẮC ====================
# Màu nền cấp 1 (background chính)
BG_PRIMARY = "#0f0f0f"

# Màu nền cấp 2 (frame con)
BG_SECONDARY = "#1a1a1a"

# Màu nền cấp 3 (card/widget)
BG_CARD = "#242424"

# Màu viền
BORDER_COLOR = "#3a3a3a"

# Màu chữ
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#a0a0a0"
TEXT_HINT = "#606060"

# Màu nút
BTN_PRIMARY = "#0078D4"
BTN_PRIMARY_HOVER = "#005A9E"
BTN_SUCCESS = "#107C10"
BTN_SUCCESS_HOVER = "#0B5C0B"
BTN_DANGER = "#D83B01"
BTN_DANGER_HOVER = "#A02F00"
BTN_DEFAULT = "#3a3a3a"
BTN_DEFAULT_HOVER = "#4a4a4a"
BTN_WARNING = "#FFAA00"

# ==================== FONT ====================
FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_SECTION = ("Segoe UI", 11, "bold")
FONT_NORMAL = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas", 10)

# ==================== KÍCH THƯỚC ====================
PADDING = 16
PADDING_SMALL = 8
BUTTON_WIDTH = 120
BUTTON_HEIGHT = 32
ENTRY_WIDTH = 120