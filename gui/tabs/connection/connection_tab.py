# ============================================================================
# gui/tabs/connection/connection_tab.py
# File chính — chỉ chứa: __init__, _create_layout, log
# Logic được tách thành 2 Mixin:
#   STM32PanelMixin      — Serial STM32: scan, connect, send, serial queue
#   RaspberryPanelMixin  — Camera Pi: connect, toggle, webcam fallback
# ============================================================================

import customtkinter as ctk
import tkinter as tk
from datetime import datetime

from gui.styles import *
from .stm32_panel     import STM32PanelMixin
from .raspberry_panel import RaspberryPanelMixin


class ConnectionTab(STM32PanelMixin, RaspberryPanelMixin, ctk.CTkFrame):
    """
    Tab Kết nối — quản lý Serial STM32 và Camera Raspberry Pi.
    Layout giữ nguyên: 2 cột trên (Serial | Camera) + Log bên dưới.
    Logic được tách:
      - stm32_panel.py     : toàn bộ Serial STM32
      - raspberry_panel.py : toàn bộ Camera Pi
    """

    def __init__(self, parent, main_window=None):
        ctk.CTkFrame.__init__(self, parent, fg_color=BG_PRIMARY)
        self.main_window = main_window

        self._create_layout()
        self.scan_ports()

        # Bắt đầu vòng lặp đọc serial (thread-safe qua after())
        self.process_serial_queue()

    # ──────────────────────────────────────────────────────────────────────────
    # LAYOUT — giữ nguyên như cũ
    # ──────────────────────────────────────────────────────────────────────────
    def _create_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="CONNECTION MANAGER",
            font=("Segoe UI", 18, "bold"), text_color=TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=2, sticky="w",
               padx=PADDING, pady=(PADDING, PADDING_SMALL))

        # Gọi UI builder từ 2 Mixin
        self._create_serial_section()    # STM32PanelMixin
        self._create_camera_section()    # RaspberryPanelMixin
        self._create_log_section()

    # ──────────────────────────────────────────────────────────────────────────
    # SYSTEM LOG
    # ──────────────────────────────────────────────────────────────────────────
    def _create_log_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.grid(row=2, column=0, columnspan=2, sticky="nsew",
                   padx=PADDING, pady=(0, PADDING))

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill=tk.X, padx=PADDING, pady=(6, 0))
        ctk.CTkLabel(header, text="SYSTEM LOG",
                     font=FONT_SECTION, text_color=TEXT_SECONDARY).pack(side=tk.LEFT)
        ctk.CTkButton(
            header, text="CLEAR", width=55, height=22,
            command=self.clear_log,
            fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER
        ).pack(side=tk.RIGHT)

        self.log_text = ctk.CTkTextbox(
            frame, height=200, font=FONT_MONO, fg_color=BG_PRIMARY)
        self.log_text.pack(fill=tk.BOTH, expand=True,
                           padx=PADDING, pady=(4, PADDING))

    def add_log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {message}\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)
        self.add_log("Log cleared.")
