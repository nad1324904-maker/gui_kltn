# ============================================================================
# gui/tabs/control_tab.py
# Tab Điều khiển chính
# Layout: Cột trái (60%) Camera Feed | Cột phải (40%) Scrollable Panel
# Chế độ MANUAL: Jog, Point Control, Teaching/Playback
# Chế độ AUTO:   Load JSON trajectory, State Machine, Thống kê PASS/FAIL
# ============================================================================

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
from datetime import datetime
from PIL import Image, ImageTk
import cv2

from gui.styles import *
from kinematics import (
    deg_to_rad, rad_to_deg,
    forward_kinematics, inverse_kinematics,
    check_reachable
)


# ============================================================
# HẰNG SỐ STATE MACHINE
# ============================================================
class AutoState:
    IDLE        = "IDLE"
    WAIT_VISION = "WAIT_VISION"
    RUNNING     = "RUNNING"


class ControlTab(ctk.CTkFrame):

    def __init__(self, parent, main_window=None):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.main_window = main_window

        # --- Thông số cơ khí ---
        self.l1 = 100.0
        self.l2 = 100.0

        # --- Trạng thái robot ---
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

        # --- Teaching / Playback ---
        self.teach_points   = []    # list of (j1°, j2°, z_mm)
        self.playback_index = 0
        self.is_playing     = False

        # --- Auto Mode ---
        self.is_auto_mode      = False
        self.auto_state        = AutoState.IDLE
        self.traj_pass         = []   # list of {"j1":..,"j2":..,"z":..}
        self.traj_fail         = []
        self.current_traj      = []
        self.current_wp_index  = 0
        self.waiting_for_stm32 = False   # cờ chờ "DONE" từ STM32
        self.count_pass        = tk.IntVar(value=0)
        self.count_fail        = tk.IntVar(value=0)

        self._create_layout()
        self.update_xy_from_joints()

        # Khởi động các vòng lặp nền
        self._update_canvas()
        self._auto_machine_tick()

    # ============================================================
    # LAYOUT CHÍNH
    # ============================================================
    def _create_layout(self):
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        # Cột trái
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, PADDING_SMALL))
        self._create_camera_section(left)

        # Cột phải (scrollable)
        right = ctk.CTkScrollableFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(PADDING_SMALL, 0))
        self._create_right_panel(right)

    # ============================================================
    # CAMERA FEED
    # ============================================================
    def _create_camera_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.BOTH, expand=True)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill=tk.X, padx=PADDING, pady=(PADDING, 4))
        ctk.CTkLabel(header, text="LIVE CAMERA FEED",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        ctk.CTkLabel(header, text="(Kết nối tại tab  Kết nối)",
                     font=("Segoe UI", 9), text_color=TEXT_HINT).pack(side=tk.LEFT, padx=8)

        self.camera_label = ctk.CTkLabel(
            frame,
            text="( Chưa kết nối camera )\nVào tab 'Kết nối' để bật camera.",
            font=FONT_NORMAL, text_color=TEXT_HINT,
            fg_color="black", corner_radius=4
        )
        self.camera_label.pack(fill=tk.BOTH, expand=True, padx=PADDING, pady=(0, PADDING))

    def _update_canvas(self):
        """Vòng lặp 33ms — lấy frame từ CameraHandler, hiển thị lên label"""
        if self.main_window:
            cam = self.main_window.camera
            if cam.is_connected:
                frame = cam.get_frame()
                if frame is not None:
                    w = self.camera_label.winfo_width()
                    h = self.camera_label.winfo_height()
                    if w > 1 and h > 1:
                        frame = cv2.resize(frame, (w, h))
                    img   = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    photo = ImageTk.PhotoImage(img)
                    self.camera_label.configure(image=photo, text="")
                    self.camera_label.image = photo  # giữ reference — KHÔNG xóa dòng này
            else:
                if self.camera_label.cget("text") == "":
                    self.camera_label.configure(
                        image=None,
                        text="( Chưa kết nối camera )\nVào tab 'Kết nối' để bật camera."
                    )
        self.after(33, self._update_canvas)

    # ============================================================
    # CỘT PHẢI
    # ============================================================
    def _create_right_panel(self, parent):
        # Nút chuyển chế độ
        self.mode_btn = ctk.CTkButton(
            parent,
            text="⚙  MANUAL MODE  —  Nhấn để chuyển AUTO",
            font=("Segoe UI", 13, "bold"), height=48,
            fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
            command=self._toggle_mode
        )
        self.mode_btn.pack(fill=tk.X, pady=(0, 4))

        self.status_bar = ctk.CTkLabel(
            parent, text="●  MANUAL MODE",
            font=FONT_NORMAL, text_color=BTN_PRIMARY
        )
        self.status_bar.pack(anchor=tk.W, pady=(0, PADDING_SMALL))

        # Frame Manual (mặc định hiển thị)
        self.manual_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.manual_frame.pack(fill=tk.X)
        self._create_status_section(self.manual_frame)
        self._create_jog_section(self.manual_frame)
        self._create_point_section(self.manual_frame)
        self._create_teaching_section(self.manual_frame)

        # Frame Auto (ẩn lúc đầu)
        self.auto_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._create_auto_section(self.auto_frame)

        # Log (luôn hiển thị)
        self._create_log_section(parent)

    # ============================================================
    # TOGGLE MANUAL / AUTO
    # ============================================================
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
            if self.auto_state != AutoState.IDLE:
                self._stop_auto()
            self.auto_frame.pack_forget()
            self.manual_frame.pack(fill=tk.X)
            self.mode_btn.configure(
                text="⚙  MANUAL MODE  —  Nhấn để chuyển AUTO",
                fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER
            )
            self.status_bar.configure(text="●  MANUAL MODE", text_color=BTN_PRIMARY)
            self.add_log("Chuyển sang MANUAL MODE.")

    # ============================================================
    # MANUAL — CURRENT STATUS
    # ============================================================
    def _create_status_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="CURRENT STATUS",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        row_xyz = ctk.CTkFrame(content, fg_color="transparent")
        row_xyz.pack(fill=tk.X, pady=2)
        for lbl, var in [("X:", self.x_pos), ("Y:", self.y_pos), ("Z:", self.z_pos)]:
            ctk.CTkLabel(row_xyz, text=lbl, font=FONT_NORMAL,
                         text_color=TEXT_SECONDARY, width=22, anchor="e").pack(side=tk.LEFT)
            ctk.CTkEntry(row_xyz, textvariable=var, width=60,
                         font=FONT_NORMAL, justify="center",
                         state="readonly").pack(side=tk.LEFT, padx=(2, 8))

        row_j = ctk.CTkFrame(content, fg_color="transparent")
        row_j.pack(fill=tk.X, pady=(4, 0))
        for lbl, var in [("θ1:", self.j1_angle), ("θ2:", self.j2_angle)]:
            ctk.CTkLabel(row_j, text=lbl, font=FONT_NORMAL,
                         text_color=TEXT_SECONDARY, width=22, anchor="e").pack(side=tk.LEFT)
            ctk.CTkEntry(row_j, textvariable=var, width=60,
                         font=FONT_NORMAL, justify="center",
                         state="readonly").pack(side=tk.LEFT, padx=(2, 16))

    # ============================================================
    # MANUAL — JOG CONTROL
    # ============================================================
    def _create_jog_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="JOG CONTROL",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        g = ctk.CTkFrame(frame, fg_color="transparent")
        g.pack(padx=PADDING, pady=(0, PADDING))
        g.grid_columnconfigure((0, 1, 2), weight=1)

        # Header
        for col, text in [(0, "J1  (°)"), (1, "J2  (°)"), (2, "Z  (mm)")]:
            ctk.CTkLabel(g, text=text, font=FONT_SECTION,
                         text_color=TEXT_SECONDARY).grid(row=0, column=col, pady=(0, 2))

        # Nút +
        for col, (txt, cmd) in enumerate([
            ("▲  J1+", lambda: self.jog_j1( self.step_size.get())),
            ("▲  J2+", lambda: self.jog_j2( self.step_size.get())),
            ("▲  Z+",  lambda: self.jog_z(  self.step_size_z.get())),
        ]):
            ctk.CTkButton(g, text=txt, width=85,
                          fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
                          command=cmd).grid(row=1, column=col, padx=3, pady=2)

        # Step entries
        ctk.CTkEntry(g, textvariable=self.step_size,   width=85, justify="center").grid(row=2, column=0, padx=3, pady=3)
        ctk.CTkEntry(g, textvariable=self.step_size,   width=85, justify="center").grid(row=2, column=1, padx=3, pady=3)
        ctk.CTkEntry(g, textvariable=self.step_size_z, width=85, justify="center").grid(row=2, column=2, padx=3, pady=3)

        # Nút -
        for col, (txt, cmd) in enumerate([
            ("▼  J1-", lambda: self.jog_j1(-self.step_size.get())),
            ("▼  J2-", lambda: self.jog_j2(-self.step_size.get())),
            ("▼  Z-",  lambda: self.jog_z( -self.step_size_z.get())),
        ]):
            ctk.CTkButton(g, text=txt, width=85,
                          fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
                          command=cmd).grid(row=3, column=col, padx=3, pady=2)

    # ============================================================
    # MANUAL — POINT CONTROL
    # ============================================================
    def _create_point_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="POINT CONTROL",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        for lbl, var in [("Target X (mm):", self.x_target),
                         ("Target Y (mm):", self.y_target),
                         ("Target Z (mm):", self.z_target)]:
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill=tk.X, pady=2)
            ctk.CTkLabel(row, text=lbl, font=FONT_NORMAL, width=110, anchor="e").pack(side=tk.LEFT)
            ctk.CTkEntry(row, textvariable=var, width=80, justify="center").pack(side=tk.LEFT, padx=6)

        ctk.CTkButton(
            content, text="MOVE TO POINT", command=self.go_to_xy,
            fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
            font=FONT_BUTTON, height=36
        ).pack(fill=tk.X, pady=(12, 4))

        row_btns = ctk.CTkFrame(content, fg_color="transparent")
        row_btns.pack(fill=tk.X)
        ctk.CTkButton(row_btns, text="Về Home", command=self.go_home,
                      fg_color=BTN_WARNING, hover_color="#D49500", width=100).pack(side=tk.LEFT, padx=(0, 4))
        ctk.CTkButton(row_btns, text="Lấy vị trí", command=self.get_position,
                      fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER, width=100).pack(side=tk.LEFT)

    # ============================================================
    # MANUAL — TEACHING / PLAYBACK
    # ============================================================
    def _create_teaching_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="TEACHING / PLAYBACK",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        # Listbox hiển thị các điểm đã dạy
        list_frame = ctk.CTkFrame(content, fg_color=BG_PRIMARY, corner_radius=4)
        list_frame.pack(fill=tk.X, pady=(0, 8))

        self.teach_listbox = tk.Listbox(
            list_frame, height=5,
            bg=BG_PRIMARY, fg=TEXT_PRIMARY,
            selectbackground=BTN_PRIMARY,
            font=("Consolas", 10), bd=0, highlightthickness=0
        )
        self.teach_listbox.pack(fill=tk.X, padx=4, pady=4)

        # Hàng nút teach
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill=tk.X, pady=2)
        ctk.CTkButton(row1, text="+ Teach Point",
                      command=self._teach_current_pos,
                      fg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER,
                      width=120).pack(side=tk.LEFT, padx=(0, 4))
        ctk.CTkButton(row1, text="Xóa điểm",
                      command=self._delete_teach_point,
                      fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
                      width=90).pack(side=tk.LEFT, padx=4)
        ctk.CTkButton(row1, text="Xóa tất cả",
                      command=self._clear_teach_points,
                      fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
                      width=90).pack(side=tk.LEFT, padx=4)

        # Hàng nút save/load/play
        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill=tk.X, pady=2)
        ctk.CTkButton(row2, text="💾 Lưu JSON",
                      command=self._save_trajectory,
                      fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
                      width=105).pack(side=tk.LEFT, padx=(0, 4))
        ctk.CTkButton(row2, text="📂 Mở JSON",
                      command=self._load_trajectory_to_teach,
                      fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
                      width=105).pack(side=tk.LEFT, padx=4)

        self.play_btn = ctk.CTkButton(
            content, text="▶  PLAY TRAJECTORY",
            command=self._toggle_playback,
            fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
            font=FONT_BUTTON, height=34
        )
        self.play_btn.pack(fill=tk.X, pady=(8, 0))

    # ============================================================
    # AUTO — SECTION
    # ============================================================
    def _create_auto_section(self, parent):
        # Nạp quỹ đạo
        traj_frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        traj_frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(traj_frame, text="TRAJECTORY FILES",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        content_t = ctk.CTkFrame(traj_frame, fg_color="transparent")
        content_t.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        # PASS file
        pass_row = ctk.CTkFrame(content_t, fg_color="transparent")
        pass_row.pack(fill=tk.X, pady=3)
        ctk.CTkButton(pass_row, text="📂 PASS Trajectory",
                      command=lambda: self._load_auto_trajectory("PASS"),
                      fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
                      width=160).pack(side=tk.LEFT)
        self.pass_file_label = ctk.CTkLabel(pass_row, text="Chưa nạp",
                                             font=("Segoe UI", 9), text_color=TEXT_HINT)
        self.pass_file_label.pack(side=tk.LEFT, padx=8)

        # FAIL file
        fail_row = ctk.CTkFrame(content_t, fg_color="transparent")
        fail_row.pack(fill=tk.X, pady=3)
        ctk.CTkButton(fail_row, text="📂 FAIL Trajectory",
                      command=lambda: self._load_auto_trajectory("FAIL"),
                      fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
                      width=160).pack(side=tk.LEFT)
        self.fail_file_label = ctk.CTkLabel(fail_row, text="Chưa nạp",
                                             font=("Segoe UI", 9), text_color=TEXT_HINT)
        self.fail_file_label.pack(side=tk.LEFT, padx=8)

        # Thống kê sản lượng
        stat_frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        stat_frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(stat_frame, text="THỐNG KÊ SẢN LƯỢNG",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        stat_content = ctk.CTkFrame(stat_frame, fg_color="transparent")
        stat_content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))
        stat_content.grid_columnconfigure((0, 1), weight=1)

        # PASS counter
        pass_box = ctk.CTkFrame(stat_content, fg_color=BG_CARD, corner_radius=6)
        pass_box.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=4)
        ctk.CTkLabel(pass_box, text="ĐẠT (PASS)", font=FONT_NORMAL,
                     text_color=BTN_SUCCESS).pack(pady=(8, 2))
        ctk.CTkLabel(pass_box, textvariable=self.count_pass,
                     font=("Segoe UI", 32, "bold"), text_color=BTN_SUCCESS).pack(pady=(0, 8))

        # FAIL counter
        fail_box = ctk.CTkFrame(stat_content, fg_color=BG_CARD, corner_radius=6)
        fail_box.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=4)
        ctk.CTkLabel(fail_box, text="LỖI (FAIL)", font=FONT_NORMAL,
                     text_color=BTN_DANGER).pack(pady=(8, 2))
        ctk.CTkLabel(fail_box, textvariable=self.count_fail,
                     font=("Segoe UI", 32, "bold"), text_color=BTN_DANGER).pack(pady=(0, 8))

        ctk.CTkButton(stat_content, text="Reset đếm",
                      command=self._reset_counters,
                      fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
                      width=100).grid(row=1, column=0, columnspan=2, pady=(0, 4))

        # Điều khiển chu kỳ
        ctrl_frame = ctk.CTkFrame(parent, fg_color=BG_SECONDARY, corner_radius=8)
        ctrl_frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(ctrl_frame, text="ĐIỀU KHIỂN CHU KỲ",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        ctrl_content = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        ctrl_content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        # Trạng thái state machine
        self.auto_state_label = ctk.CTkLabel(
            ctrl_content,
            text="Trạng thái: IDLE",
            font=FONT_NORMAL, text_color=TEXT_HINT
        )
        self.auto_state_label.pack(anchor=tk.W, pady=(0, 8))

        self.start_auto_btn = ctk.CTkButton(
            ctrl_content, text="▶  START AUTO",
            command=self._start_auto,
            fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
            font=("Segoe UI", 13, "bold"), height=40
        )
        self.start_auto_btn.pack(fill=tk.X, pady=(0, 4))

        ctk.CTkButton(
            ctrl_content, text="⚠  EMERGENCY STOP",
            command=self._stop_auto,
            fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
            font=("Segoe UI", 13, "bold"), height=40
        ).pack(fill=tk.X)

    # ============================================================
    # LOG
    # ============================================================
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

    # ============================================================
    # TEACHING LOGIC
    # ============================================================
    def _teach_current_pos(self):
        pt = (round(self.j1_angle.get(), 2),
              round(self.j2_angle.get(), 2),
              round(self.z_pos.get(), 2))
        self.teach_points.append(pt)
        idx = len(self.teach_points)
        self.teach_listbox.insert(tk.END,
            f"P{idx:02d}  J1={pt[0]:7.2f}°  J2={pt[1]:7.2f}°  Z={pt[2]:6.2f}mm")
        self.add_log(f"Teach P{idx:02d}: J1={pt[0]}, J2={pt[1]}, Z={pt[2]}")

    def _delete_teach_point(self):
        sel = self.teach_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.teach_listbox.delete(idx)
        self.teach_points.pop(idx)
        self.add_log(f"Đã xóa điểm P{idx+1:02d}.")

    def _clear_teach_points(self):
        if not self.teach_points:
            return
        if messagebox.askyesno("Xác nhận", "Xóa toàn bộ điểm đã dạy?"):
            self.teach_points.clear()
            self.teach_listbox.delete(0, tk.END)
            self.add_log("Đã xóa toàn bộ teach points.")

    def _save_trajectory(self):
        if not self.teach_points:
            messagebox.showwarning("Cảnh báo", "Chưa có điểm nào để lưu!")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Lưu quỹ đạo"
        )
        if not path:
            return
        data = [{"j1": p[0], "j2": p[1], "z": p[2]} for p in self.teach_points]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"waypoints": data}, f, indent=2)
            self.add_log(f"Đã lưu {len(data)} điểm → {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file:\n{e}")

    def _load_trajectory_to_teach(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Mở quỹ đạo"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            waypoints = data.get("waypoints", [])
            if not waypoints:
                raise ValueError("File không có trường 'waypoints'.")
            self.teach_points.clear()
            self.teach_listbox.delete(0, tk.END)
            for i, wp in enumerate(waypoints):
                pt = (wp["j1"], wp["j2"], wp["z"])
                self.teach_points.append(pt)
                self.teach_listbox.insert(tk.END,
                    f"P{i+1:02d}  J1={pt[0]:7.2f}°  J2={pt[1]:7.2f}°  Z={pt[2]:6.2f}mm")
            self.add_log(f"Nạp {len(waypoints)} điểm từ {os.path.basename(path)}")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            messagebox.showerror("Lỗi đọc file", f"File JSON không hợp lệ:\n{e}")

    def _toggle_playback(self):
        if not self.is_playing:
            if not self.teach_points:
                messagebox.showwarning("Cảnh báo", "Chưa có điểm nào để playback!")
                return
            self.is_playing     = True
            self.playback_index = 0
            self.play_btn.configure(text="⏹  STOP PLAYBACK", fg_color=BTN_DANGER)
            self.add_log(f"Bắt đầu playback {len(self.teach_points)} điểm...")
            self._playback_tick()
        else:
            self.is_playing = False
            self.play_btn.configure(text="▶  PLAY TRAJECTORY", fg_color=BTN_SUCCESS)
            self.add_log("Playback đã dừng.")

    def _playback_tick(self):
        """Gửi từng waypoint cách nhau 500ms (không dùng while True)"""
        if not self.is_playing or self.playback_index >= len(self.teach_points):
            self.is_playing = False
            self.play_btn.configure(text="▶  PLAY TRAJECTORY", fg_color=BTN_SUCCESS)
            self.add_log("Playback hoàn thành.")
            return
        pt = self.teach_points[self.playback_index]
        self.send_command(f"J1 {pt[0]}")
        self.send_command(f"J2 {pt[1]}")
        self.send_command(f"Z {pt[2]}")
        self.j1_angle.set(pt[0])
        self.j2_angle.set(pt[1])
        self.z_pos.set(pt[2])
        self.update_xy_from_joints()
        self.add_log(f"Playback P{self.playback_index+1:02d}: J1={pt[0]}, J2={pt[1]}, Z={pt[2]}")
        self.playback_index += 1
        self.after(500, self._playback_tick)

    # ============================================================
    # AUTO LOGIC
    # ============================================================
    def _load_auto_trajectory(self, kind: str):
        """Nạp file JSON cho PASS hoặc FAIL trajectory"""
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title=f"Nạp quỹ đạo {kind}"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            waypoints = data.get("waypoints", [])
            if not waypoints:
                raise ValueError("File không có trường 'waypoints'.")
            # Validate từng waypoint
            for wp in waypoints:
                if not all(k in wp for k in ("j1", "j2", "z")):
                    raise ValueError("Waypoint thiếu key j1/j2/z.")
            if kind == "PASS":
                self.traj_pass = waypoints
                self.pass_file_label.configure(
                    text=f"✓ {os.path.basename(path)} ({len(waypoints)} pts)",
                    text_color=BTN_SUCCESS
                )
            else:
                self.traj_fail = waypoints
                self.fail_file_label.configure(
                    text=f"✓ {os.path.basename(path)} ({len(waypoints)} pts)",
                    text_color=BTN_DANGER
                )
            self.add_log(f"Nạp {kind}: {len(waypoints)} waypoints từ {os.path.basename(path)}")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            messagebox.showerror("Lỗi đọc file", f"File JSON không hợp lệ:\n{e}")

    def _reset_counters(self):
        self.count_pass.set(0)
        self.count_fail.set(0)
        self.add_log("Reset bộ đếm sản lượng.")

    def _start_auto(self):
        if not self.traj_pass or not self.traj_fail:
            messagebox.showwarning("Cảnh báo", "Chưa nạp đủ PASS và FAIL trajectory!")
            return
        self.auto_state        = AutoState.WAIT_VISION
        self.waiting_for_stm32 = False
        self._set_auto_state_label("WAIT_VISION", BTN_WARNING)
        self.start_auto_btn.configure(state="disabled")
        self.add_log("AUTO START — Đang chờ tín hiệu từ Raspberry Pi...")

    def _stop_auto(self):
        self.auto_state        = AutoState.IDLE
        self.waiting_for_stm32 = False
        self.current_traj      = []
        self.current_wp_index  = 0
        self.send_command("STOP")
        self.start_auto_btn.configure(state="normal")
        self._set_auto_state_label("IDLE", TEXT_HINT)
        self.add_log("⚠  EMERGENCY STOP — Auto dừng.")

    def _set_auto_state_label(self, state_str: str, color):
        self.auto_state_label.configure(
            text=f"Trạng thái: {state_str}",
            text_color=color
        )

    def notify_stm32_done(self):
        """
        Được gọi từ connection_tab khi nhận chuỗi "DONE" từ STM32.
        Hạ cờ chờ để state machine tiếp tục waypoint tiếp theo.
        """
        self.waiting_for_stm32 = False

    # ============================================================
    # STATE MACHINE — chạy mỗi 100ms qua after(), không dùng while True
    # ============================================================
    def _auto_machine_tick(self):
        try:
            if self.auto_state == AutoState.WAIT_VISION:
                self._tick_wait_vision()
            elif self.auto_state == AutoState.RUNNING:
                self._tick_running()
        except Exception as e:
            self.add_log(f"ERROR state machine: {e}")
            self._stop_auto()
        finally:
            self.after(100, self._auto_machine_tick)

    def _tick_wait_vision(self):
        """Hỏi socket_handler xem Pi đã gửi tín hiệu chưa"""
        if not self.main_window:
            return
        socket_h = getattr(self.main_window, "socket_handler", None)
        if socket_h is None:
            return  # socket_handler chưa được khởi tạo — bỏ qua

        signal = socket_h.get_signal()  # trả về "PASS", "FAIL", hoặc None
        if signal is None:
            return

        if signal == "PASS":
            self.current_traj     = list(self.traj_pass)
            self.current_wp_index = 0
            self.add_log("Vision → PASS. Bắt đầu PASS trajectory.")
        elif signal == "FAIL":
            self.current_traj     = list(self.traj_fail)
            self.current_wp_index = 0
            self.add_log("Vision → FAIL. Bắt đầu FAIL trajectory.")
        else:
            self.add_log(f"Vision → Tín hiệu không xác định: {signal}")
            return

        self.auto_state        = AutoState.RUNNING
        self.waiting_for_stm32 = False
        self._set_auto_state_label("RUNNING", BTN_PRIMARY)

    def _tick_running(self):
        """Gửi lần lượt từng waypoint, chờ STM32 "DONE" trước khi gửi tiếp"""
        if self.waiting_for_stm32:
            return  # Đang chờ STM32 xác nhận xong điểm hiện tại

        if self.current_wp_index >= len(self.current_traj):
            # Hoàn thành toàn bộ quỹ đạo
            self._on_trajectory_complete()
            return

        wp = self.current_traj[self.current_wp_index]
        self.send_command(f"J1 {wp['j1']}")
        self.send_command(f"J2 {wp['j2']}")
        self.send_command(f"Z {wp['z']}")
        self.add_log(
            f"Auto WP{self.current_wp_index+1}: "
            f"J1={wp['j1']}, J2={wp['j2']}, Z={wp['z']}"
        )

        self.waiting_for_stm32 = True
        self.current_wp_index  += 1

    def _on_trajectory_complete(self):
        """Gọi khi robot chạy xong 1 quỹ đạo hoàn chỉnh"""
        # Phân biệt PASS/FAIL dựa trên trajectory đang chạy
        if self.current_traj == self.traj_pass:
            self.count_pass.set(self.count_pass.get() + 1)
            self.add_log(f"✓ Hoàn thành PASS #{self.count_pass.get()}")
        else:
            self.count_fail.set(self.count_fail.get() + 1)
            self.add_log(f"✗ Hoàn thành FAIL #{self.count_fail.get()}")

        # Quay lại chờ tín hiệu tiếp theo từ Pi
        self.current_traj      = []
        self.current_wp_index  = 0
        self.waiting_for_stm32 = False
        self.auto_state        = AutoState.WAIT_VISION
        self._set_auto_state_label("WAIT_VISION", BTN_WARNING)
        self.add_log("Chờ phôi tiếp theo từ Raspberry Pi...")

    # ============================================================
    # GỬI LỆNH
    # ============================================================
    def send_command(self, cmd: str) -> bool:
        serial_h = self.main_window.serial if self.main_window else None
        if serial_h and serial_h.is_connected:
            if serial_h.send_command(cmd):
                self.add_log(f"TX: {cmd}")
                return True
        else:
            self.add_log("Cảnh báo: Chưa kết nối Serial!")
        return False

    # ============================================================
    # JOG
    # ============================================================
    def jog_j1(self, delta: float):
        new = round((self.j1_angle.get() + delta) % 360.0, 2)
        self.send_command(f"J1 {new}")
        self.j1_angle.set(new)
        self.update_xy_from_joints()

    def jog_j2(self, delta: float):
        new = round((self.j2_angle.get() + delta) % 360.0, 2)
        self.send_command(f"J2 {new}")
        self.j2_angle.set(new)
        self.update_xy_from_joints()

    def jog_z(self, delta: float):
        new = round(self.z_pos.get() + delta, 2)
        self.send_command(f"Z {new}")
        self.z_pos.set(new)

    # ============================================================
    # POINT CONTROL (IK)
    # ============================================================
    def go_to_xy(self):
        x, y, z = self.x_target.get(), self.y_target.get(), self.z_target.get()
        reachable, msg, _ = check_reachable(x, y, z, self.l1, self.l2)
        if not reachable:
            self.add_log(f"ERROR IK: ({x:.1f}, {y:.1f}, {z:.1f}) — {msg}")
            return
        result = inverse_kinematics(x, y, z, self.l1, self.l2, solution='elbow_up')
        if result:
            q1, q2, dz = result
            j1d, j2d   = rad_to_deg(q1), rad_to_deg(q2)
            self.send_command(f"J1 {j1d:.1f}")
            self.send_command(f"J2 {j2d:.1f}")
            self.send_command(f"Z {dz:.1f}")
            self.j1_angle.set(round(j1d, 2))
            self.j2_angle.set(round(j2d, 2))
            self.z_pos.set(round(dz, 2))
            self.update_xy_from_joints()
        else:
            self.add_log(f"ERROR IK: không tìm được nghiệm cho ({x:.1f}, {y:.1f})")

    def go_home(self):
        self.send_command("J1 0")
        self.send_command("J2 0")
        self.send_command("Z 0")
        self.j1_angle.set(0.0)
        self.j2_angle.set(0.0)
        self.z_pos.set(0.0)
        self.update_xy_from_joints()
        self.add_log("→ Home position.")

    def get_position(self):
        self.send_command("GET")

    # ============================================================
    # TIỆN ÍCH
    # ============================================================
    def update_xy_from_joints(self):
        x, y, z = forward_kinematics(
            deg_to_rad(self.j1_angle.get()),
            deg_to_rad(self.j2_angle.get()),
            self.z_pos.get(),
            self.l1, self.l2
        )
        self.x_pos.set(round(x, 2))
        self.y_pos.set(round(y, 2))
        self.z_pos.set(round(z, 2))

    def add_log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {message}\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)
        self.add_log("Log cleared.")