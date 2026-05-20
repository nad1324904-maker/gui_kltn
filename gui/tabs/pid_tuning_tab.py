# ============================================================================
# gui/tabs/pid_tuning_tab.py (v2 - Multi-Joint Support)
# Tab tinh chỉnh PID: Hỗ trợ lưu thông số riêng cho J1, J2, và Z
# ============================================================================

import customtkinter as ctk
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

from gui.styles import *

class PIDTuningTab(ctk.CTkFrame):
    def __init__(self, parent, main_window=None):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.main_window = main_window
        
        # 1. Bộ nhớ PID cho từng khớp (Dictionary)
        self.pid_memory = {
            "J1": [1.25, 0.08, 0.42],  # Kp, Ki, Kd default cho J1
            "J2": [1.00, 0.05, 0.30],  # Kp, Ki, Kd default cho J2
            "Z":  [2.00, 0.50, 0.10]   # Kp, Ki, Kd default cho Z
        }
        
        # Biến trạng thái
        self.selected_joint = tk.StringVar(value="J1")
        self.prev_joint = "J1" # Dùng để lưu lại giá trị cũ trước khi chuyển
        self.is_locked = tk.BooleanVar(value=True)
        
        # Thông số PID đang hiển thị trên UI
        self.kp = tk.DoubleVar(value=self.pid_memory["J1"][0])
        self.ki = tk.DoubleVar(value=self.pid_memory["J1"][1])
        self.kd = tk.DoubleVar(value=self.pid_memory["J1"][2])
        
        # Lắng nghe sự thay đổi của Radio Button để chuyển đổi PID
        self.selected_joint.trace_add("write", self._on_joint_switch)
        
        # Dữ liệu vẽ đồ thị
        self.time_data = []
        self.sp_data = []
        self.pv_data = []
        
        self.create_layout()

    # ============================================================================
    # LOGIC CHUYỂN ĐỔI THÔNG SỐ (CORE UPDATE)
    # ============================================================================
    def _on_joint_switch(self, *args):
        """Hàm tự động gọi khi người dùng click chọn J1, J2 hoặc Z"""
        # 1. Lưu thông số hiện tại của motor cũ vào bộ nhớ
        self.pid_memory[self.prev_joint] = [self.kp.get(), self.ki.get(), self.kd.get()]
        
        # 2. Cập nhật motor mới
        new_joint = self.selected_joint.get()
        self.prev_joint = new_joint
        
        # 3. Nạp thông số của motor mới từ bộ nhớ lên các ô nhập liệu
        vals = self.pid_memory[new_joint]
        self.kp.set(vals[0])
        self.ki.set(vals[1])
        self.kd.set(vals[2])
        
        if self.main_window:
            self.main_window.tabs["connection"].add_log(f"PID Tuning: Chuyển sang cấu hình {new_joint}")

    def update_pid_to_hardware(self):
        """Gửi lệnh PID xuống STM32 dựa trên motor đang chọn"""
        joint = self.selected_joint.get()
        kp, ki, kd = self.kp.get(), self.ki.get(), self.kd.get()
        
        # Xác định tiền tố lệnh dựa trên motor
        # PID1 cho J1, PID2 cho J2, PIDD cho Z (D1)
        prefix = "PID1" if joint == "J1" else "PID2" if joint == "J2" else "PIDD"
        cmd = f"{prefix} {kp:.3f} {ki:.3f} {kd:.3f}"
        
        if self.main_window:
            success = self.main_window.tabs["connection"].send_command(cmd)
            if success:
                self.main_window.tabs["control"].add_log(f"Gửi PID mới cho {joint}: {kp}/{ki}/{kd}")

    # ============================================================================
    # TẠO BỐ CỤC GIAO DIỆN
    # ============================================================================
    def create_layout(self):
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        # CỘT TRÁI: ĐỒ THỊ
        left_col = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, PADDING_SMALL))
        self.create_graphs_section(left_col)

        # CỘT PHẢI: ĐIỀU KHIỂN
        right_col = ctk.CTkScrollableFrame(self, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(PADDING_SMALL, 0))
        
        self.create_joint_selection(right_col)
        self.create_pid_gains_section(right_col)
        self.create_step_test_section(right_col)
        self.create_performance_section(right_col)
        self.create_live_state_section(right_col)

    def create_graphs_section(self, parent):
        ctk.CTkLabel(parent, text="PID RESPONSE GRAPHS", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(pady=(12, 0))
        self.fig = Figure(figsize=(6, 8), dpi=100, facecolor='#2B2B2B')
        
        # Đồ thị 1: Position
        self.ax1 = self.fig.add_subplot(211, facecolor='#1E1E1E')
        self.ax1.set_title("Position Response", color='white')
        self.ax1.tick_params(colors='white')
        self.ax1.grid(color='#404040', linestyle='--')
        
        # Đồ thị 2: Velocity
        self.ax2 = self.fig.add_subplot(212, facecolor='#1E1E1E')
        self.ax2.set_title("Velocity Response", color='white')
        self.ax2.set_xlabel("Time (s)", color='white')
        self.ax2.tick_params(colors='white')
        self.ax2.grid(color='#404040', linestyle='--')
        
        self.fig.tight_layout(pad=3.0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def create_joint_selection(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))
        ctk.CTkLabel(frame, text="CHỌN MOTOR TINH CHỈNH", font=FONT_SECTION, text_color=TEXT_SECONDARY).pack(anchor="w", padx=PADDING, pady=(8, 4))
        
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill=tk.X, padx=PADDING, pady=(0, 8))
        ctk.CTkRadioButton(row, text="Joint 1", variable=self.selected_joint, value="J1").pack(side=tk.LEFT, padx=(0, 16))
        ctk.CTkRadioButton(row, text="Joint 2", variable=self.selected_joint, value="J2").pack(side=tk.LEFT, padx=16)
        ctk.CTkRadioButton(row, text="Trục Z", variable=self.selected_joint, value="Z").pack(side=tk.LEFT, padx=(16, 0))

    def create_pid_gains_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=PADDING_SMALL)
        
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill=tk.X, padx=PADDING, pady=(8, 4))
        ctk.CTkLabel(header, text="THÔNG SỐ PID", font=FONT_SECTION, text_color=TEXT_SECONDARY).pack(side=tk.LEFT)
        
        self.btn_lock = ctk.CTkButton(header, text="🔒 Khóa", width=60, height=24, fg_color=BTN_DANGER, command=self.toggle_lock)
        self.btn_lock.pack(side=tk.RIGHT)
        
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))
        
        self.kp_entry = self.add_gain_row(content, "Kp:", self.kp)
        self.ki_entry = self.add_gain_row(content, "Ki:", self.ki)
        self.kd_entry = self.add_gain_row(content, "Kd:", self.kd)
        
        self.btn_update_pid = ctk.CTkButton(
            content, text="CẬP NHẬT XUỐNG HARDWARE", 
            font=FONT_BUTTON, fg_color=BTN_PRIMARY,
            command=self.update_pid_to_hardware # GỌI HÀM GỬI LỆNH MỚI
        )
        self.btn_update_pid.pack(pady=(12, 0), fill=tk.X)
        self.apply_lock_state()

    def add_gain_row(self, parent, label_text, variable):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, pady=4)
        ctk.CTkLabel(row, text=label_text, width=30, anchor="w").pack(side=tk.LEFT)
        entry = ctk.CTkEntry(row, textvariable=variable, width=70, justify="center")
        entry.pack(side=tk.RIGHT)
        return entry

    # (Các hàm khác như create_step_test_section, create_performance_section giữ nguyên như file cũ...)

    def toggle_lock(self):
        if self.is_locked.get():
            dialog = ctk.CTkInputDialog(text="Nhập mật khẩu (1234):", title="Bảo mật")
            if dialog.get_input() == "1234":
                self.is_locked.set(False)
                self.apply_lock_state()
        else:
            self.is_locked.set(True)
            self.apply_lock_state()
        
    def apply_lock_state(self):
        state = "readonly" if self.is_locked.get() else "normal"
        self.kp_entry.configure(state=state)
        self.ki_entry.configure(state=state)
        self.kd_entry.configure(state=state)
        self.btn_update_pid.configure(state="disabled" if self.is_locked.get() else "normal")

    def create_step_test_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=PADDING_SMALL)
        ctk.CTkLabel(frame, text="STEP TEST SETTINGS", font=FONT_SECTION, text_color=TEXT_SECONDARY).pack(anchor="w", padx=PADDING, pady=(8, 4))
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill=tk.X, padx=PADDING, pady=4)
        ctk.CTkLabel(row, text="Setpoint Step (°/mm):").pack(side=tk.LEFT)
        ctk.CTkEntry(row, width=60, justify="center").pack(side=tk.RIGHT)
        ctk.CTkButton(frame, text="CHẠY THỬ ĐÁP ỨNG BƯỚC", fg_color=BTN_WARNING, text_color="black", font=FONT_BUTTON).pack(fill=tk.X, padx=PADDING, pady=(8, 4))
        ctk.CTkButton(frame, text="DỪNG KHẨN CẤP", fg_color=BTN_DANGER, font=FONT_BUTTON).pack(fill=tk.X, padx=PADDING, pady=(0, 12))

    def create_performance_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=PADDING_SMALL)
        ctk.CTkLabel(frame, text="RESPONSE PERFORMANCE", font=FONT_SECTION, text_color=TEXT_SECONDARY).pack(anchor="w", padx=PADDING, pady=(8, 4))
        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill=tk.X, padx=PADDING, pady=(0, 12))
        grid.grid_columnconfigure((0,1), weight=1)
        self.add_metric(grid, 0, 0, "Overshoot (%)", "0.0")
        self.add_metric(grid, 0, 1, "Settling Time (s)", "0.0")
        self.add_metric(grid, 1, 0, "Rise Time (s)", "0.0")
        self.add_metric(grid, 1, 1, "SS Error", "0.0")

    def add_metric(self, parent, row, col, label, value):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, pady=4)
        ctk.CTkLabel(f, text=label, text_color=TEXT_HINT, font=("Segoe UI", 11)).pack()
        ctk.CTkLabel(f, text=value, font=("Segoe UI", 18, "bold")).pack()

    def create_live_state_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=PADDING_SMALL)
        ctk.CTkLabel(frame, text="LIVE ROBOT STATE", font=FONT_SECTION, text_color=TEXT_SECONDARY).pack(anchor="w", padx=PADDING, pady=(8, 4))
        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))
        self.add_state_row(content, "J1 Angle (°):", "0.0")
        self.add_state_row(content, "J2 Angle (°):", "0.0")
        self.add_state_row(content, "Z Position (mm):", "0.0")

    def add_state_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, pady=2)
        ctk.CTkLabel(row, text=label).pack(side=tk.LEFT)
        ctk.CTkEntry(row, width=70, justify="center", state="readonly").pack(side=tk.RIGHT)