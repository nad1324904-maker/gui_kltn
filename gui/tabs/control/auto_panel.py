import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
from gui.styles import *

class AutoPanel(ctk.CTkFrame):
    class AutoState:
        IDLE        = "IDLE"
        WAIT_VISION = "WAIT_VISION"
        RUNNING     = "RUNNING"

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        self.auto_state        = self.AutoState.IDLE
        self.traj_pass         = []
        self.traj_fail         = []
        self.current_traj      = []
        self.current_wp_index  = 0
        self.waiting_for_stm32 = False
        self.count_pass        = tk.IntVar(value=0)
        self.count_fail        = tk.IntVar(value=0)

        self._create_auto_section()
        self._auto_machine_tick()

    def _create_auto_section(self):
        traj_frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        traj_frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(traj_frame, text="TRAJECTORY FILES",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        content_t = ctk.CTkFrame(traj_frame, fg_color="transparent")
        content_t.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        pass_row = ctk.CTkFrame(content_t, fg_color="transparent")
        pass_row.pack(fill=tk.X, pady=3)
        ctk.CTkButton(pass_row, text="📂 PASS Trajectory",
                      command=lambda: self._load_auto_trajectory("PASS"),
                      fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
                      width=160).pack(side=tk.LEFT)
        self.pass_file_label = ctk.CTkLabel(pass_row, text="Chưa nạp",
                                             font=("Segoe UI", 9), text_color=TEXT_HINT)
        self.pass_file_label.pack(side=tk.LEFT, padx=8)

        fail_row = ctk.CTkFrame(content_t, fg_color="transparent")
        fail_row.pack(fill=tk.X, pady=3)
        ctk.CTkButton(fail_row, text="📂 FAIL Trajectory",
                      command=lambda: self._load_auto_trajectory("FAIL"),
                      fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
                      width=160).pack(side=tk.LEFT)
        self.fail_file_label = ctk.CTkLabel(fail_row, text="Chưa nạp",
                                             font=("Segoe UI", 9), text_color=TEXT_HINT)
        self.fail_file_label.pack(side=tk.LEFT, padx=8)

        stat_frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        stat_frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(stat_frame, text="THỐNG KÊ SẢN LƯỢNG",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        stat_content = ctk.CTkFrame(stat_frame, fg_color="transparent")
        stat_content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))
        stat_content.grid_columnconfigure((0, 1), weight=1)

        pass_box = ctk.CTkFrame(stat_content, fg_color=BG_CARD, corner_radius=6)
        pass_box.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=4)
        ctk.CTkLabel(pass_box, text="ĐẠT (PASS)", font=FONT_NORMAL,
                     text_color=BTN_SUCCESS).pack(pady=(8, 2))
        ctk.CTkLabel(pass_box, textvariable=self.count_pass,
                     font=("Segoe UI", 32, "bold"), text_color=BTN_SUCCESS).pack(pady=(0, 8))

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

        ctrl_frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        ctrl_frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(ctrl_frame, text="ĐIỀU KHIỂN CHU KỲ",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        ctrl_content = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        ctrl_content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

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

    def _load_auto_trajectory(self, kind: str):
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
            self.controller.add_log(f"Nạp {kind}: {len(waypoints)} waypoints từ {os.path.basename(path)}")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            messagebox.showerror("Lỗi đọc file", f"File JSON không hợp lệ:\n{e}")

    def _reset_counters(self):
        self.count_pass.set(0)
        self.count_fail.set(0)
        self.controller.add_log("Reset bộ đếm sản lượng.")

    def _start_auto(self):
        if not self.traj_pass or not self.traj_fail:
            messagebox.showwarning("Cảnh báo", "Chưa nạp đủ PASS và FAIL trajectory!")
            return
        self.auto_state        = self.AutoState.WAIT_VISION
        self.waiting_for_stm32 = False
        self._set_auto_state_label("WAIT_VISION", BTN_WARNING)
        self.start_auto_btn.configure(state="disabled")
        self.controller.add_log("AUTO START — Đang chờ tín hiệu từ Raspberry Pi...")

    def _stop_auto(self):
        self.auto_state        = self.AutoState.IDLE
        self.waiting_for_stm32 = False
        self.current_traj      = []
        self.current_wp_index  = 0
        self.controller.robot_panel.send_command("STOP")
        self.start_auto_btn.configure(state="normal")
        self._set_auto_state_label("IDLE", TEXT_HINT)
        self.controller.add_log("⚠  EMERGENCY STOP — Auto dừng.")

    def _set_auto_state_label(self, state_str: str, color):
        self.auto_state_label.configure(
            text=f"Trạng thái: {state_str}",
            text_color=color
        )

    def notify_stm32_done(self):
        self.waiting_for_stm32 = False

    def _auto_machine_tick(self):
        try:
            if self.auto_state == self.AutoState.WAIT_VISION:
                self._tick_wait_vision()
            elif self.auto_state == self.AutoState.RUNNING:
                self._tick_running()
        except Exception as e:
            self.controller.add_log(f"ERROR state machine: {e}")
            self._stop_auto()
        finally:
            self.after(100, self._auto_machine_tick)

    def _tick_wait_vision(self):
        if not self.controller.main_window:
            return
        socket_h = getattr(self.controller.main_window, "socket_handler", None)
        if socket_h is None:
            return

        signal = socket_h.get_signal()
        if signal is None:
            return

        if signal == "PASS":
            self.current_traj     = list(self.traj_pass)
            self.current_wp_index = 0
            self.controller.add_log("Vision → PASS. Bắt đầu PASS trajectory.")
        elif signal == "FAIL":
            self.current_traj     = list(self.traj_fail)
            self.current_wp_index = 0
            self.controller.add_log("Vision → FAIL. Bắt đầu FAIL trajectory.")
        else:
            self.controller.add_log(f"Vision → Tín hiệu không xác định: {signal}")
            return

        self.auto_state        = self.AutoState.RUNNING
        self.waiting_for_stm32 = False
        self._set_auto_state_label("RUNNING", BTN_PRIMARY)

    def _tick_running(self):
        if self.waiting_for_stm32:
            return

        if self.current_wp_index >= len(self.current_traj):
            self._on_trajectory_complete()
            return

        wp = self.current_traj[self.current_wp_index]
        self.controller.robot_panel.send_command(f"J1 {wp['j1']}")
        self.controller.robot_panel.send_command(f"J2 {wp['j2']}")
        self.controller.robot_panel.send_command(f"Z {wp['z']}")
        self.controller.add_log(
            f"Auto WP{self.current_wp_index+1}: "
            f"J1={wp['j1']}, J2={wp['j2']}, Z={wp['z']}"
        )

        self.waiting_for_stm32 = True
        self.current_wp_index  += 1

    def _on_trajectory_complete(self):
        if self.current_traj == self.traj_pass:
            self.count_pass.set(self.count_pass.get() + 1)
            self.controller.add_log(f"✓ Hoàn thành PASS #{self.count_pass.get()}")
        else:
            self.count_fail.set(self.count_fail.get() + 1)
            self.controller.add_log(f"✗ Hoàn thành FAIL #{self.count_fail.get()}")

        self.current_traj      = []
        self.current_wp_index  = 0
        self.waiting_for_stm32 = False
        self.auto_state        = self.AutoState.WAIT_VISION
        self._set_auto_state_label("WAIT_VISION", BTN_WARNING)
        self.controller.add_log("Chờ phôi tiếp theo từ Raspberry Pi...")