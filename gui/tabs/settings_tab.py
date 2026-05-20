# ============================================================================
# gui/tabs/settings_tab.py (v2)
# Tab Cài đặt — Cấu hình cơ khí và thông số Motor (Đã loại bỏ PID sang tab PID Tuning)
# ============================================================================

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os

from gui.styles import *

class SettingsTab(ctk.CTkFrame):

    def __init__(self, parent, main_window=None):
        super().__init__(parent, fg_color=BG_PRIMARY)

        self.main_window = main_window
        self.config_file = "robot_config.json"
        self.is_unlocked = False
        self.password    = "scara2025"

        # ============================================================
        # THÔNG SỐ CƠ KHÍ
        # ============================================================
        self.l1    = tk.DoubleVar(value=100.0)
        self.l2    = tk.DoubleVar(value=100.0)
        self.q1_min = tk.DoubleVar(value=-90.0)
        self.q1_max = tk.DoubleVar(value=90.0)
        self.q2_min = tk.DoubleVar(value=-45.0)
        self.q2_max = tk.DoubleVar(value=45.0)
        self.z_min  = tk.DoubleVar(value=0.0)
        self.z_max  = tk.DoubleVar(value=150.0)

        # ============================================================
        # THÔNG SỐ KHỚP J1 (Motor & Gear)
        # ============================================================
        self.encoder_ppr_j1 = tk.IntVar(value=400)
        self.gear_ratio_j1  = tk.IntVar(value=50)
        self.dir_j1         = tk.IntVar(value=1)       # 1 hoặc -1
        self.vmax_j1        = tk.DoubleVar(value=60.0) # °/s
        self.acc_j1         = tk.DoubleVar(value=30.0) # °/s²

        # ============================================================
        # THÔNG SỐ KHỚP J2 (Motor & Gear)
        # ============================================================
        self.encoder_ppr_j2 = tk.IntVar(value=400)
        self.gear_ratio_j2  = tk.IntVar(value=50)
        self.dir_j2         = tk.IntVar(value=1)
        self.vmax_j2        = tk.DoubleVar(value=60.0)
        self.acc_j2         = tk.DoubleVar(value=30.0)

        # ============================================================
        # THÔNG SỐ TRỤC D1 (Vít me - Linear)
        # ============================================================
        self.encoder_ppr_d1 = tk.IntVar(value=400)
        self.lead_d1        = tk.DoubleVar(value=8.0)  # mm/vòng
        self.dir_d1         = tk.IntVar(value=1)
        self.vmax_d1        = tk.DoubleVar(value=20.0) # mm/s
        self.acc_d1         = tk.DoubleVar(value=10.0) # mm/s²

        # ============================================================
        # GIAO DIỆN
        # ============================================================
        self._create_unlock_section()
        self._create_settings_sections()
        self.lock_settings()
        self.load_config()

    # ============================================================
    # SECTION: BẢO MẬT
    # ============================================================
    def _create_unlock_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=0)
        frame.pack(fill=tk.X, padx=PADDING, pady=PADDING)

        ctk.CTkLabel(frame, text="SECURITY", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(PADDING, PADDING_SMALL)
        )

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        ctk.CTkLabel(row, text="Password", font=FONT_NORMAL, text_color=TEXT_SECONDARY).pack(side=tk.LEFT)

        self.password_entry = ctk.CTkEntry(row, width=200, show="•", font=FONT_NORMAL)
        self.password_entry.pack(side=tk.LEFT, padx=12)
        self.password_entry.bind("<Return>", self.check_password)

        ctk.CTkButton(
            row, text="UNLOCK", command=self.check_password,
            width=100, height=32, fg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER, font=FONT_BUTTON
        ).pack(side=tk.LEFT, padx=4)

        self.lock_status = ctk.CTkLabel(row, text="Locked", font=FONT_NORMAL, text_color=BTN_DANGER)
        self.lock_status.pack(side=tk.LEFT, padx=24)

    # ============================================================
    # SECTION: CÀI ĐẶT CHÍNH
    # ============================================================
    def _create_settings_sections(self):
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_frame.pack(fill=tk.BOTH, expand=True, padx=PADDING, pady=(0, 0))

        main_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # Cột trái: Mechanical
        self._create_mechanical_section(main_frame)

        # Cột phải: Motor Specs cho J1, J2, D1
        right = ctk.CTkFrame(main_frame, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(PADDING_SMALL, 0))
        self._create_joint_section(right, joint="J1")
        self._create_joint_section(right, joint="J2")
        self._create_d1_section(right)

        # Nút hành động
        self._create_button_row()

    def _create_mechanical_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="MECHANICAL", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(PADDING, PADDING_SMALL)
        )

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        rows = [
            ("Link 1 length (mm)",  self.l1,    "l1_entry"),
            ("Link 2 length (mm)",  self.l2,    "l2_entry"),
            ("Z min (mm)",          self.z_min, "z_min_entry"),
            ("Z max (mm)",          self.z_max, "z_max_entry"),
        ]
        for i, (label, var, attr) in enumerate(rows):
            ctk.CTkLabel(content, text=label, font=FONT_NORMAL, text_color=TEXT_SECONDARY).grid(
                row=i, column=0, pady=8, sticky=tk.W
            )
            entry = ctk.CTkEntry(content, textvariable=var, width=120, font=FONT_NORMAL)
            entry.grid(row=i, column=1, pady=8, padx=12)
            setattr(self, attr, entry)

        # Separator
        ctk.CTkFrame(content, height=1, fg_color=BORDER_COLOR).grid(
            row=len(rows), column=0, columnspan=2, sticky="ew", pady=12
        )

        # Joint angle limits
        limit_rows = [
            ("J1 limits (°)", self.q1_min, self.q1_max, "q1_min_entry", "q1_max_entry"),
            ("J2 limits (°)", self.q2_min, self.q2_max, "q2_min_entry", "q2_max_entry"),
        ]
        for i, (label, var_min, var_max, attr_min, attr_max) in enumerate(limit_rows):
            row_idx = len(rows) + 1 + i
            ctk.CTkLabel(content, text=label, font=FONT_NORMAL, text_color=TEXT_SECONDARY).grid(
                row=row_idx, column=0, pady=8, sticky=tk.W
            )
            pair = ctk.CTkFrame(content, fg_color="transparent")
            pair.grid(row=row_idx, column=1, pady=8)
            e_min = ctk.CTkEntry(pair, textvariable=var_min, width=65, font=FONT_NORMAL)
            e_min.pack(side=tk.LEFT)
            ctk.CTkLabel(pair, text="→", font=FONT_NORMAL, text_color=TEXT_SECONDARY).pack(side=tk.LEFT, padx=4)
            e_max = ctk.CTkEntry(pair, textvariable=var_max, width=65, font=FONT_NORMAL)
            e_max.pack(side=tk.LEFT)
            setattr(self, attr_min, e_min)
            setattr(self, attr_max, e_max)

    def _create_joint_section(self, parent, joint="J1"):
        j = joint.lower()
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text=f"MOTOR {joint}", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(PADDING, PADDING_SMALL)
        )

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        motor_rows = [
            ("Encoder PPR:",  getattr(self, f"encoder_ppr_{j}"), f"ppr{j[-1]}_entry"),
            ("Gear ratio:",   getattr(self, f"gear_ratio_{j}"),  f"gear{j[-1]}_entry"),
            ("Vmax (°/s):",   getattr(self, f"vmax_{j}"),        f"vmax{j[-1]}_entry"),
            ("Acc (°/s²):",   getattr(self, f"acc_{j}"),         f"acc{j[-1]}_entry"),
        ]
        for i, (label, var, attr) in enumerate(motor_rows):
            ctk.CTkLabel(content, text=label, font=FONT_NORMAL, text_color=TEXT_SECONDARY, width=110, anchor="e").grid(
                row=i, column=0, pady=4, sticky=tk.E
            )
            entry = ctk.CTkEntry(content, textvariable=var, width=90, font=FONT_NORMAL)
            entry.grid(row=i, column=1, pady=4, padx=(8, 24))
            setattr(self, attr, entry)

        # Direction
        ctk.CTkLabel(content, text="Direction:", font=FONT_NORMAL, text_color=TEXT_SECONDARY, width=110, anchor="e").grid(
            row=len(motor_rows), column=0, pady=4, sticky=tk.E
        )
        dir_frame = ctk.CTkFrame(content, fg_color="transparent")
        dir_frame.grid(row=len(motor_rows), column=1, pady=4, padx=(8, 24), sticky=tk.W)
        dir_var = getattr(self, f"dir_{j}")
        ctk.CTkRadioButton(dir_frame, text="+1", variable=dir_var, value=1,  font=FONT_NORMAL).pack(side=tk.LEFT, padx=4)
        ctk.CTkRadioButton(dir_frame, text="-1", variable=dir_var, value=-1, font=FONT_NORMAL).pack(side=tk.LEFT, padx=4)
        setattr(self, f"dir{j[-1]}_frame", dir_frame)

    def _create_d1_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="MOTOR D1 (Linear)", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(PADDING, PADDING_SMALL)
        )

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        motor_rows = [
            ("Encoder PPR:",        self.encoder_ppr_d1, "pprd_entry"),
            ("Lead screw (mm/rev):", self.lead_d1,       "lead_d1_entry"),
            ("Vmax (mm/s):",        self.vmax_d1,        "vmaxd_entry"),
            ("Acc (mm/s²):",        self.acc_d1,         "accd_entry"),
        ]
        for i, (label, var, attr) in enumerate(motor_rows):
            ctk.CTkLabel(content, text=label, font=FONT_NORMAL, text_color=TEXT_SECONDARY, width=140, anchor="e").grid(
                row=i, column=0, pady=4, sticky=tk.E
            )
            entry = ctk.CTkEntry(content, textvariable=var, width=90, font=FONT_NORMAL)
            entry.grid(row=i, column=1, pady=4, padx=(8, 24))
            setattr(self, attr, entry)

        # Direction
        ctk.CTkLabel(content, text="Direction:", font=FONT_NORMAL, text_color=TEXT_SECONDARY, width=140, anchor="e").grid(
            row=len(motor_rows), column=0, pady=4, sticky=tk.E
        )
        dir_frame = ctk.CTkFrame(content, fg_color="transparent")
        dir_frame.grid(row=len(motor_rows), column=1, pady=4, padx=(8, 24), sticky=tk.W)
        ctk.CTkRadioButton(dir_frame, text="+1", variable=self.dir_d1, value=1,  font=FONT_NORMAL).pack(side=tk.LEFT, padx=4)
        ctk.CTkRadioButton(dir_frame, text="-1", variable=self.dir_d1, value=-1, font=FONT_NORMAL).pack(side=tk.LEFT, padx=4)
        self.dird_frame = dir_frame

    def _create_button_row(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        self.save_btn = ctk.CTkButton(
            frame, text="SAVE CONFIG", command=self.save_config,
            fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
            width=140, height=36, font=FONT_BUTTON, state=tk.DISABLED
        )
        self.save_btn.pack(side=tk.LEFT, padx=4)

        self.reset_btn = ctk.CTkButton(
            frame, text="RESET", command=self.reset_to_default,
            fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
            width=100, height=36, font=FONT_BUTTON, state=tk.DISABLED
        )
        self.reset_btn.pack(side=tk.LEFT, padx=4)

        self.apply_btn = ctk.CTkButton(
            frame, text="APPLY", command=self.apply_settings,
            fg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER,
            width=140, height=36, font=FONT_BUTTON, state=tk.DISABLED
        )
        self.apply_btn.pack(side=tk.LEFT, padx=4)

        self.status_label = ctk.CTkLabel(frame, text="", font=FONT_NORMAL, text_color=TEXT_SECONDARY)
        self.status_label.pack(side=tk.RIGHT)

    # ============================================================
    # LOCK / UNLOCK
    # ============================================================
    def _all_entries(self):
        return [
            self.l1_entry, self.l2_entry, self.z_min_entry, self.z_max_entry,
            self.q1_min_entry, self.q1_max_entry, self.q2_min_entry, self.q2_max_entry,
            self.ppr1_entry, self.gear1_entry, self.vmax1_entry, self.acc1_entry,
            self.ppr2_entry, self.gear2_entry, self.vmax2_entry, self.acc2_entry,
            self.pprd_entry, self.lead_d1_entry, self.vmaxd_entry, self.accd_entry,
        ]

    def _all_radiobuttons(self):
        frames = [self.dir1_frame, self.dir2_frame, self.dird_frame]
        widgets = []
        for f in frames:
            for w in f.winfo_children():
                widgets.append(w)
        return widgets

    def check_password(self, event=None):
        if self.password_entry.get() == self.password:
            self.is_unlocked = True
            self.unlock_settings()
            self.lock_status.configure(text="Unlocked", text_color=BTN_SUCCESS)
            self.password_entry.delete(0, tk.END)
            self.add_status("Unlocked", BTN_SUCCESS)
        else:
            messagebox.showerror("Error", "Wrong password!")

    def unlock_settings(self):
        for e in self._all_entries(): e.configure(state=tk.NORMAL)
        for rb in self._all_radiobuttons(): rb.configure(state=tk.NORMAL)
        self.save_btn.configure(state=tk.NORMAL)
        self.reset_btn.configure(state=tk.NORMAL)
        self.apply_btn.configure(state=tk.NORMAL)

    def lock_settings(self):
        for e in self._all_entries(): e.configure(state=tk.DISABLED)
        for rb in self._all_radiobuttons(): rb.configure(state=tk.DISABLED)
        self.save_btn.configure(state=tk.DISABLED)
        self.reset_btn.configure(state=tk.DISABLED)
        self.apply_btn.configure(state=tk.DISABLED)

    # ============================================================
    # LOAD / SAVE / APPLY
    # ============================================================
    def load_config(self):
        if not os.path.exists(self.config_file): return
        try:
            with open(self.config_file, 'r') as f: d = json.load(f)
            self.l1.set(d.get('l1', 100.0)); self.l2.set(d.get('l2', 100.0))
            self.z_min.set(d.get('z_min', 0.0)); self.z_max.set(d.get('z_max', 150.0))
            self.q1_min.set(d.get('q1_min_deg', -90.0)); self.q1_max.set(d.get('q1_max_deg', 90.0))
            self.q2_min.set(d.get('q2_min_deg', -45.0)); self.q2_max.set(d.get('q2_max_deg', 45.0))
            self.encoder_ppr_j1.set(d.get('encoder_ppr_j1', 400)); self.gear_ratio_j1.set(d.get('gear_ratio_j1', 50))
            self.dir_j1.set(d.get('dir_j1', 1)); self.vmax_j1.set(d.get('vmax_j1', 60.0)); self.acc_j1.set(d.get('acc_j1', 30.0))
            self.encoder_ppr_j2.set(d.get('encoder_ppr_j2', 400)); self.gear_ratio_j2.set(d.get('gear_ratio_j2', 50))
            self.dir_j2.set(d.get('dir_j2', 1)); self.vmax_j2.set(d.get('vmax_j2', 60.0)); self.acc_j2.set(d.get('acc_j2', 30.0))
            self.encoder_ppr_d1.set(d.get('encoder_ppr_d1', 400)); self.lead_d1.set(d.get('lead_d1', 8.0))
            self.dir_d1.set(d.get('dir_d1', 1)); self.vmax_d1.set(d.get('vmax_d1', 20.0)); self.acc_d1.set(d.get('acc_d1', 10.0))
            self.add_status("Config loaded", BTN_SUCCESS)
        except: pass

    def save_config(self):
        data = {
            'l1': self.l1.get(), 'l2': self.l2.get(), 'z_min': self.z_min.get(), 'z_max': self.z_max.get(),
            'q1_min_deg': self.q1_min.get(), 'q1_max_deg': self.q1_max.get(),
            'q2_min_deg': self.q2_min.get(), 'q2_max_deg': self.q2_max.get(),
            'encoder_ppr_j1': self.encoder_ppr_j1.get(), 'gear_ratio_j1': self.gear_ratio_j1.get(),
            'dir_j1': self.dir_j1.get(), 'vmax_j1': self.vmax_j1.get(), 'acc_j1': self.acc_j1.get(),
            'encoder_ppr_j2': self.encoder_ppr_j2.get(), 'gear_ratio_j2': self.gear_ratio_j2.get(),
            'dir_j2': self.dir_j2.get(), 'vmax_j2': self.vmax_j2.get(), 'acc_j2': self.acc_j2.get(),
            'encoder_ppr_d1': self.encoder_ppr_d1.get(), 'lead_d1': self.lead_d1.get(),
            'dir_d1': self.dir_d1.get(), 'vmax_d1': self.vmax_d1.get(), 'acc_d1': self.acc_d1.get(),
        }
        try:
            with open(self.config_file, 'w') as f: json.dump(data, f, indent=4)
            self.add_status("Config saved", BTN_SUCCESS)
        except: pass

    def reset_to_default(self):
        if not messagebox.askyesno("Confirm", "Reset to default?"): return
        self.l1.set(100.0); self.l2.set(100.0); self.z_min.set(0.0); self.z_max.set(150.0)
        self.vmax_j1.set(60.0); self.acc_j1.set(30.0); self.vmax_j2.set(60.0); self.acc_j2.set(30.0)
        self.add_status("Reset defaults", BTN_WARNING)

    def apply_settings(self):
        # Đồng bộ l1/l2 sang Control Tab
        ctrl = self.main_window.tabs.get("control") if self.main_window else None
        if ctrl:
            ctrl.l1 = self.l1.get()
            ctrl.l2 = self.l2.get()
            ctrl.update_xy_from_joints()

        # Gửi VMAX/ACC xuống STM32 nếu đang kết nối
        serial_h = self.main_window.serial if self.main_window else None
        if serial_h and serial_h.is_connected:
            conn = self.main_window.tabs.get("connection")
            if conn:
                cmds = [
                    f"VMAX1 {self.vmax_j1.get()}", f"VMAX2 {self.vmax_j2.get()}", f"VMAXD {self.vmax_d1.get()}",
                    f"ACC1 {self.acc_j1.get()}", f"ACC2 {self.acc_j2.get()}", f"ACCD {self.acc_d1.get()}",
                ]
                conn._send_cmd_queue(cmds, index=0)

        self._update_robot_params_file()
        self.add_status("Settings applied", BTN_SUCCESS)

    def _update_robot_params_file(self):
        try:
            os.makedirs("kinematics", exist_ok=True)
            with open("kinematics/robot_params.py", "w", encoding="utf-8") as f:
                f.write(f"""import math
L1 = {self.l1.get()}
L2 = {self.l2.get()}
Z_MIN = {self.z_min.get()}
Z_MAX = {self.z_max.get()}
Q1_MIN_DEG = {self.q1_min.get()}
Q1_MAX_DEG = {self.q1_max.get()}
Q2_MIN_DEG = {self.q2_min.get()}
Q2_MAX_DEG = {self.q2_max.get()}

ENCODER_PPR_J1 = {self.encoder_ppr_j1.get()}
GEAR_RATIO_J1  = {self.gear_ratio_j1.get()}
DIR_J1         = {self.dir_j1.get()}
ENCODER_PPR_J2 = {self.encoder_ppr_j2.get()}
GEAR_RATIO_J2  = {self.gear_ratio_j2.get()}
DIR_J2         = {self.dir_j2.get()}
ENCODER_PPR_D1 = {self.encoder_ppr_d1.get()}
LEAD_D1        = {self.lead_d1.get()}
DIR_D1         = {self.dir_d1.get()}
""")
        except: pass

    def add_status(self, message, color):
        self.status_label.configure(text=message, text_color=color)
        self.after(3000, lambda: self.status_label.configure(text=""))
