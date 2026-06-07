# ============================================================================
# gui/tabs/simulation/sim_panels.py
# Mixin: tất cả UI builder — status, IK, FK, teaching panel, LED, input_row
# ============================================================================

import customtkinter as ctk
import tkinter as tk
from gui.styles import *


class SimPanelsMixin:

    # ──────────────────────────────────────────────────────────────────────────
    # STATUS PANEL
    # ──────────────────────────────────────────────────────────────────────────
    def _build_status_panel(self):
        self.btn_mode = ctk.CTkButton(
            self.right_frame, text="MODE: VIRTUAL SIM",
            fg_color=BTN_DEFAULT, height=36, font=FONT_BUTTON,
            command=self.toggle_mode)
        self.btn_mode.pack(fill=tk.X, padx=8, pady=(10, 8))

        card = ctk.CTkFrame(self.right_frame, fg_color=BG_CARD)
        card.pack(fill=tk.X, padx=8, pady=4)

        title_row = ctk.CTkFrame(card, fg_color="transparent")
        title_row.pack(fill=tk.X, padx=10, pady=(8, 2))
        ctk.CTkLabel(title_row, text="LIVE STATUS", font=FONT_SECTION).pack(side=tk.LEFT)

        self.led_canvas = tk.Canvas(title_row, width=16, height=16,
                                    bg=BG_CARD, highlightthickness=0)
        self.led_canvas.pack(side=tk.RIGHT, padx=4)
        self._led = self.led_canvas.create_oval(2, 2, 14, 14, fill="#555", outline="")

        self.lbl_xyz = ctk.CTkLabel(card, text="X: 0.0 | Y: 0.0 | Z: 0.0",
                                    font=FONT_NORMAL, text_color="#00ffcc")
        self.lbl_xyz.pack(pady=2)
        self.lbl_joints = ctk.CTkLabel(card, text="J1: 0.0° | J2: 0.0°",
                                       font=("Segoe UI", 11), text_color=TEXT_HINT)
        self.lbl_joints.pack(pady=(0, 4))
        self.lbl_reach = ctk.CTkLabel(card, text="● IN WORKSPACE",
                                      font=("Segoe UI", 10, "bold"),
                                      text_color=BTN_SUCCESS)
        self.lbl_reach.pack(pady=(0, 8))

    # ──────────────────────────────────────────────────────────────────────────
    # IK PANEL
    # ──────────────────────────────────────────────────────────────────────────
    def _build_ik_panel(self):
        card = ctk.CTkFrame(self.right_frame, fg_color=BG_CARD)
        card.pack(fill=tk.X, padx=8, pady=6)
        ctk.CTkLabel(card, text="INVERSE KINEMATICS", font=FONT_SECTION).pack(pady=(8, 4))

        self.ent_x    = self._input_row(card, "Target X (mm):")
        self.ent_y    = self._input_row(card, "Target Y (mm):")
        self.ent_z_ik = self._input_row(card, "Target Z (mm):")

        elbow_row = ctk.CTkFrame(card, fg_color="transparent")
        elbow_row.pack(fill=tk.X, padx=10, pady=4)
        ctk.CTkLabel(elbow_row, text="Elbow:", width=60, anchor="w").pack(side=tk.LEFT)
        ctk.CTkRadioButton(elbow_row, text="Up",   variable=self.ik_solution,
                           value=0, command=self._refresh_ik_preview).pack(side=tk.LEFT, padx=4)
        ctk.CTkRadioButton(elbow_row, text="Down", variable=self.ik_solution,
                           value=1, command=self._refresh_ik_preview).pack(side=tk.LEFT, padx=4)

        ctk.CTkButton(card, text="SOLVE IK & MOVE",
                      fg_color=BTN_PRIMARY,
                      command=self.solve_virtual_ik).pack(pady=(6, 10), padx=16, fill=tk.X)

    # ──────────────────────────────────────────────────────────────────────────
    # FK PANEL
    # ──────────────────────────────────────────────────────────────────────────
    def _build_fk_panel(self):
        card = ctk.CTkFrame(self.right_frame, fg_color=BG_CARD)
        card.pack(fill=tk.X, padx=8, pady=6)
        ctk.CTkLabel(card, text="FORWARD KINEMATICS", font=FONT_SECTION).pack(pady=(8, 4))

        self.ent_j1 = self._input_row(card, "Angle J1 (°):")
        self.ent_j2 = self._input_row(card, "Angle J2 (°):")
        self.ent_sz = self._input_row(card, "Height Z (mm):")

        ctk.CTkButton(card, text="SOLVE FK & MOVE",
                      fg_color="#404060",
                      command=self.solve_virtual_fk).pack(pady=(6, 10), padx=16, fill=tk.X)

    # ──────────────────────────────────────────────────────────────────────────
    # TEACHING / PLAYBACK PANEL
    # ──────────────────────────────────────────────────────────────────────────
    def _build_trajectory_panel(self):
        card = ctk.CTkFrame(self.right_frame, fg_color=BG_CARD)
        card.pack(fill=tk.X, padx=8, pady=6)
        ctk.CTkLabel(card, text="TEACHING / PLAYBACK", font=FONT_SECTION).pack(pady=(8, 4))

        # Nhập tọa độ
        rec_frame = ctk.CTkFrame(card, fg_color="transparent")
        rec_frame.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.ent_teach_x = self._input_row(rec_frame, "X (mm):")
        self.ent_teach_y = self._input_row(rec_frame, "Y (mm):")
        self.ent_teach_z = self._input_row(rec_frame, "Z (mm):")
        ctk.CTkButton(rec_frame, text="+ RECORD POINT",
                      fg_color=BTN_SUCCESS, height=28,
                      font=("Segoe UI", 9, "bold"),
                      command=self.teach_record_point).pack(fill=tk.X, pady=(6, 2))

        # Danh sách điểm
        self.teach_listbox = tk.Listbox(
            card, bg="#0D0D1A", fg="#00ffcc",
            selectbackground="#0F3460",
            font=("Consolas", 9), height=5,
            highlightthickness=0, bd=0)
        self.teach_listbox.pack(fill=tk.X, padx=10, pady=4)

        # Xóa điểm / xóa tất cả
        del_row = ctk.CTkFrame(card, fg_color="transparent")
        del_row.pack(fill=tk.X, padx=10, pady=2)
        ctk.CTkButton(del_row, text="✕ XÓA ĐIỂM",
                      fg_color=BTN_DANGER, height=26,
                      font=("Segoe UI", 9, "bold"),
                      command=self.teach_remove_point).pack(side=tk.LEFT, expand=True, padx=(0, 3))
        ctk.CTkButton(del_row, text="🗑 XÓA TẤT CẢ",
                      fg_color="#444", height=26,
                      font=("Segoe UI", 9, "bold"),
                      command=self.teach_clear_all).pack(side=tk.LEFT, expand=True, padx=(3, 0))

        # Save / Load
        io_row = ctk.CTkFrame(card, fg_color="transparent")
        io_row.pack(fill=tk.X, padx=10, pady=2)
        ctk.CTkButton(io_row, text="💾 SAVE",
                      fg_color=BTN_PRIMARY, height=26,
                      font=("Segoe UI", 9, "bold"),
                      command=self.teach_save).pack(side=tk.LEFT, expand=True, padx=(0, 3))
        ctk.CTkButton(io_row, text="📂 LOAD",
                      fg_color=BTN_DEFAULT, height=26,
                      font=("Segoe UI", 9, "bold"),
                      command=self.teach_load).pack(side=tk.LEFT, expand=True, padx=(3, 0))

        # Trạng thái playback
        self.lbl_playback_status = ctk.CTkLabel(
            card, text="⏹ Chờ lệnh...",
            font=("Segoe UI", 9), text_color=TEXT_HINT)
        self.lbl_playback_status.pack(pady=(4, 2))

        # Start / Stop
        pb_row = ctk.CTkFrame(card, fg_color="transparent")
        pb_row.pack(fill=tk.X, padx=10, pady=(2, 10))
        self.btn_play = ctk.CTkButton(
            pb_row, text="▶ START",
            fg_color=BTN_PRIMARY, height=32,
            font=("Segoe UI", 10, "bold"),
            command=self.teach_start)
        self.btn_play.pack(side=tk.LEFT, expand=True, padx=(0, 3))
        ctk.CTkButton(
            pb_row, text="■ STOP",
            fg_color=BTN_DANGER, height=32,
            font=("Segoe UI", 10, "bold"),
            command=self.teach_stop).pack(side=tk.LEFT, expand=True, padx=(3, 0))

    # ──────────────────────────────────────────────────────────────────────────
    # LED & REACH STATUS
    # ──────────────────────────────────────────────────────────────────────────
    def _update_led(self, in_ws: bool):
        color = "#00ff88" if in_ws else "#FF3333"
        self.led_canvas.itemconfig(self._led, fill=color)
        self.lbl_reach.configure(
            text="● IN WORKSPACE" if in_ws else "● OUT OF RANGE",
            text_color=BTN_SUCCESS if in_ws else BTN_DANGER)

    def _set_reach_status(self, ok: bool):
        pass  # LED cập nhật mỗi frame, giữ để tương thích

    # ──────────────────────────────────────────────────────────────────────────
    # UI UTILITY
    # ──────────────────────────────────────────────────────────────────────────
    def _input_row(self, parent, label_text, default=""):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, padx=10, pady=2)
        ctk.CTkLabel(row, text=label_text, width=110, anchor="w",
                     font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ent = ctk.CTkEntry(row, width=75, justify="center", font=("Consolas", 10))
        if default:
            ent.insert(0, default)
        ent.pack(side=tk.RIGHT)
        return ent