import customtkinter as ctk
import tkinter as tk
from datetime import datetime

from gui.styles import *
from .camera_panel import CameraPanel
from .robot_panel import RobotPanel
from .teaching_panel import TeachingPanel
from .auto_panel import AutoPanel

class ControlTab(ctk.CTkFrame):
    def __init__(self, parent, main_window=None):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.main_window = main_window

        # --- Thông số cơ khí ---
        self.l1 = 100.0
        self.l2 = 100.0

        # --- Trạng thái robot chung ---
        self.j1_angle = tk.DoubleVar(value=0.0)
        self.j2_angle = tk.DoubleVar(value=0.0)
        self.x_pos    = tk.DoubleVar(value=0.0)
        self.y_pos    = tk.DoubleVar(value=0.0)
        self.z_pos    = tk.DoubleVar(value=0.0)
        self.x_target = tk.DoubleVar(value=0.0)
        self.y_target = tk.DoubleVar(value=0.0)
        self.z_target = tk.DoubleVar(value=0.0)
        self.step_size   = tk.DoubleVar(value=5.0)
        self.step_size_z = tk.DoubleVar(value=10.0)

        # Trạng thái hệ thống
        self.is_auto_mode = False

        self._create_layout()
        
        # Cập nhật vị trí ban đầu
        self.robot_panel.update_xy_from_joints()

    def _create_layout(self):
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        # Cột trái: Camera
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, PADDING_SMALL))
        self.camera_panel = CameraPanel(left, self)
        self.camera_panel.pack(fill=tk.BOTH, expand=True)

        # Cột phải (scrollable): Điều khiển
        right = ctk.CTkScrollableFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(PADDING_SMALL, 0))

        # Nút chuyển đổi mode
        self.mode_btn = ctk.CTkButton(
            right,
            text="⚙  MANUAL MODE  —  Nhấn để chuyển AUTO",
            font=("Segoe UI", 13, "bold"), height=48,
            fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
            command=self._toggle_mode
        )
        self.mode_btn.pack(fill=tk.X, pady=(0, 4))

        self.status_bar = ctk.CTkLabel(
            right, text="●  MANUAL MODE",
            font=FONT_NORMAL, text_color=BTN_PRIMARY
        )
        self.status_bar.pack(anchor=tk.W, pady=(0, PADDING_SMALL))

        # Khung Manual
        self.manual_frame = ctk.CTkFrame(right, fg_color="transparent")
        self.manual_frame.pack(fill=tk.X)
        
        self.robot_panel = RobotPanel(self.manual_frame, self)
        self.robot_panel.pack(fill=tk.X)
        
        self.teaching_panel = TeachingPanel(self.manual_frame, self)
        self.teaching_panel.pack(fill=tk.X)

        # Khung Auto (ẩn lúc đầu)
        self.auto_frame = ctk.CTkFrame(right, fg_color="transparent")
        self.auto_panel = AutoPanel(self.auto_frame, self)
        self.auto_panel.pack(fill=tk.X)

        # Hệ thống Log (luôn hiển thị cuối cùng)
        self._create_log_section(right)

    def _toggle_mode(self):
        self.is_auto_mode = not self.is_auto_mode
        if self.is_auto_mode:
            self.manual_frame.pack_forget()
            self.auto_frame.pack(fill=tk.X)
            self.mode_btn.configure(
                text="🤖  AUTO MODE  —  Nhấn để chuyển MANUAL",
                fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER
            )
            self.status_bar.configure(text="●  AUTO MODE", text_color=BTN_SUCCESS)
            self.add_log("Chuyển sang AUTO MODE.")
        else:
            if self.auto_panel.auto_state != self.auto_panel.AutoState.IDLE:
                self.auto_panel._stop_auto()
            self.auto_frame.pack_forget()
            self.manual_frame.pack(fill=tk.X)
            self.mode_btn.configure(
                text="⚙  MANUAL MODE  —  Nhấn để chuyển AUTO",
                fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER
            )
            self.status_bar.configure(text="●  MANUAL MODE", text_color=BTN_PRIMARY)
            self.add_log("Chuyển sang MANUAL MODE.")

    def _create_log_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(PADDING_SMALL, 0))

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill=tk.X, padx=PADDING, pady=(6, 0))
        ctk.CTkLabel(header, text="SYSTEM LOG",
                     font=FONT_SECTION, text_color=TEXT_SECONDARY).pack(side=tk.LEFT)
        ctk.CTkButton(header, text="CLEAR", width=55, height=22,
                      command=self.clear_log,
                      fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER).pack(side=tk.RIGHT)

        self.log_text = ctk.CTkTextbox(frame, height=110, font=FONT_MONO, fg_color=BG_PRIMARY)
        self.log_text.pack(fill=tk.X, padx=PADDING, pady=(4, PADDING))

    def add_log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {message}\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)
        self.add_log("Log cleared.")

    # Wrapper để nhận tín hiệu từ STM32 (từ Connection Tab gọi sang)
    def notify_stm32_done(self):
        self.auto_panel.notify_stm32_done()