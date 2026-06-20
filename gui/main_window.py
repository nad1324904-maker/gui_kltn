# ============================================================================
# gui/main_window.py
# Khung xương chính: Sidebar + quản lý Tab
# Giữ SerialHandler và CameraHandler dùng chung cho toàn bộ ứng dụng
# ============================================================================

import customtkinter as ctk
import tkinter as tk

from communication.serial_handler import SerialHandler
from communication.camera_handler import CameraHandler
from communication.socket_handler import SocketHandler

from gui.tabs.connection import ConnectionTab
from gui.tabs.control.control_tab import ControlTab
from gui.tabs.pid_tuning_tab import PIDTuningTab
from gui.tabs.settings_tab   import SettingsTab
from gui.tabs.simulation import SimulationTab

from gui.styles import *


class MainWindow:
    """Quản lý cửa sổ chính với giao diện Sidebar hiện đại"""

    def __init__(self, root):
        self.root = root
        self.root.title("SCARA Robot Control - Professional HMI")
        self.root.geometry("1200x800")
        self.root.minsize(1050, 700)

        # ============================================================
        # HANDLER DÙNG CHUNG — khởi tạo 1 lần, tất cả tab truy cập qua đây
        # ============================================================
        self.serial = SerialHandler()
        self.camera = CameraHandler()
        self.socket_handler = SocketHandler(port=5005) 
        self.socket_handler.start_server() # Bắt đầu mở cửa chờ Pi kết nối
        # Grid gốc: 1 hàng, 2 cột (sidebar | nội dung)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # ==========================================
        # 1. SIDEBAR
        # ==========================================
        self.sidebar_frame = ctk.CTkFrame(
            self.root, width=220, corner_radius=0, fg_color=BG_SECONDARY
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="ROBOT - SCARA",
            font=("Segoe UI", 22, "bold"), text_color=BTN_PRIMARY
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 40))

        _btn = dict(
            corner_radius=0, height=50, border_spacing=10,
            text_color=TEXT_PRIMARY, fg_color="transparent",
            hover_color=BG_CARD, anchor="w", font=FONT_BUTTON
        )

        self.btn_control = ctk.CTkButton(
            self.sidebar_frame, text="  Điều khiển Robot",
            command=lambda: self.show_tab("control"), **_btn
        )
        self.btn_control.grid(row=1, column=0, sticky="ew")

        self.btn_pid = ctk.CTkButton(
            self.sidebar_frame, text="  PID & Đồ thị",
            command=lambda: self.show_tab("pid"), **_btn
        )
        self.btn_pid.grid(row=2, column=0, sticky="ew")

        self.btn_settings = ctk.CTkButton(
            self.sidebar_frame, text="  Cài đặt Hệ thống",
            command=lambda: self.show_tab("settings"), **_btn
        )
        self.btn_settings.grid(row=3, column=0, sticky="ew")

        self.btn_simulation = ctk.CTkButton(
            self.sidebar_frame, text="  Mô phỏng 3D",
            command=lambda: self.show_tab("simulation"), **_btn
        )
        self.btn_simulation.grid(row=4, column=0, sticky="ew")

        self.btn_connection = ctk.CTkButton(
            self.sidebar_frame, text="  Kết nối",
            command=lambda: self.show_tab("connection"), **_btn
        )
        self.btn_connection.grid(row=5, column=0, sticky="ew")

        # ==========================================
        # 2. VÙNG NỘI DUNG
        # ==========================================
        self.main_frame = ctk.CTkFrame(
            self.root, fg_color=BG_PRIMARY, corner_radius=0
        )
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Khởi tạo Tab — thứ tự các tab cũ không đổi, connection thêm vào cuối
        self.tabs = {}
        self.tabs["control"]    = ControlTab(self.main_frame, main_window=self)
        self.tabs["pid"]        = PIDTuningTab(self.main_frame)
        self.tabs["settings"]   = SettingsTab(self.main_frame, main_window=self)
        # Lưu ý: SettingsTab cần được cập nhật constructor từ control_tab → main_window
        self.tabs["simulation"] = SimulationTab(self.main_frame, main_window=self)
        self.tabs["connection"] = ConnectionTab(self.main_frame, main_window=self)

        self.show_tab("control")

    # ============================================================
    # CHUYỂN TAB
    # ============================================================
    def show_tab(self, tab_name):
        btn_map = {
            "control":    self.btn_control,
            "pid":        self.btn_pid,
            "settings":   self.btn_settings,
            "simulation": self.btn_simulation,
            "connection": self.btn_connection,
        }
        for name, btn in btn_map.items():
            btn.configure(fg_color=BG_CARD if name == tab_name else "transparent")

        for name, frame in self.tabs.items():
            if name == tab_name:
                frame.pack(fill=tk.BOTH, expand=True)
            else:
                frame.pack_forget()