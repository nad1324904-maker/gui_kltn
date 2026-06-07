# ============================================================================
# gui/tabs/simulation/simulation_tab.py
# File chính — chỉ chứa: __init__, properties, create_layout, render_loop
# Kế thừa logic từ 4 Mixin:
#   SimKinematicsMixin  — IK/FK, lerp, clamp, workspace
#   SimPlotsMixin       — Matplotlib 3D/2D init và vẽ
#   SimTeachingMixin    — Teaching/Playback
#   SimPanelsMixin      — UI builder
# ============================================================================

import customtkinter as ctk
import tkinter as tk

from gui.styles import *
from .sim_kinematics import SimKinematicsMixin
from .sim_plots      import SimPlotsMixin
from .sim_teaching   import SimTeachingMixin
from .sim_panels     import SimPanelsMixin


class SimulationTab(SimKinematicsMixin, SimPlotsMixin,
                    SimTeachingMixin, SimPanelsMixin,
                    ctk.CTkFrame):
    """
    Tab Mô phỏng 3D — Virtual Simulation cho SCARA PRR
    Logic được tách thành 4 Mixin để dễ bảo trì:
      - sim_kinematics.py : toán học IK/FK, lerp, workspace
      - sim_plots.py      : Matplotlib 3D/2D
      - sim_teaching.py   : Teaching/Playback trajectory
      - sim_panels.py     : UI builder
    """

    LERP_SPEED = 0.04

    # ──────────────────────────────────────────────────────────────────────────
    # PROPERTIES — đọc thông số từ settings_tab mỗi frame (luôn mới nhất)
    # ──────────────────────────────────────────────────────────────────────────
    def _settings(self):
        if self.main_window and hasattr(self.main_window, 'tabs'):
            return self.main_window.tabs.get("settings")
        return None

    @property
    def L1(self):
        s = self._settings(); return s.l1.get() if s else 100.0

    @property
    def L2(self):
        s = self._settings(); return s.l2.get() if s else 100.0

    @property
    def Z_MAX(self):
        s = self._settings(); return s.z_max.get() if s else 200.0

    @property
    def J1_MIN(self):
        s = self._settings(); return s.q1_min.get() if s else -150.0

    @property
    def J1_MAX(self):
        s = self._settings(); return s.q1_max.get() if s else 150.0

    @property
    def J2_MIN(self):
        s = self._settings(); return s.q2_min.get() if s else -150.0

    @property
    def J2_MAX(self):
        s = self._settings(); return s.q2_max.get() if s else 150.0

    # ──────────────────────────────────────────────────────────────────────────
    # KHỞI TẠO
    # ──────────────────────────────────────────────────────────────────────────
    def __init__(self, parent, main_window=None):
        ctk.CTkFrame.__init__(self, parent, fg_color=BG_PRIMARY)
        self.main_window = main_window
        self.control_tab = None

        # Trạng thái khớp simulation
        self.sim_j1 = tk.DoubleVar(value=45.0)
        self.sim_j2 = tk.DoubleVar(value=-90.0)
        self.sim_z  = tk.DoubleVar(value=0.0)

        # Đích lerp
        self._tgt_j1 = self.sim_j1.get()
        self._tgt_j2 = self.sim_j2.get()
        self._tgt_z  = self.sim_z.get()

        # Digital twin
        self.is_digital_twin = tk.BooleanVar(value=False)

        # IK solution
        self.ik_solution  = tk.IntVar(value=0)   # 0=elbow_up, 1=elbow_down
        self._ik_solutions = []

        # Teaching
        self.waypoints: list[tuple[float, float, float]] = []
        self._traj_running = False
        self._traj_index   = 0

        self.create_layout()
        self.init_plots()
        self.render_loop()

    # ──────────────────────────────────────────────────────────────────────────
    # LAYOUT
    # ──────────────────────────────────────────────────────────────────────────
    def create_layout(self):
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.frame_3d = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        self.frame_3d.grid(row=0, column=0, sticky="nsew", padx=(0, PADDING_SMALL))

        self.frame_2d = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        self.frame_2d.grid(row=0, column=1, sticky="nsew", padx=(0, PADDING_SMALL))
        ctk.CTkLabel(self.frame_2d, text="TOP VIEW",
                     font=FONT_SECTION, text_color=TEXT_HINT).pack(pady=(8, 0))

        self.right_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG_SECONDARY, corner_radius=8)
        self.right_frame.grid(row=0, column=2, sticky="nsew")

        # Gọi các panel builder từ SimPanelsMixin
        self._build_status_panel()
        self._build_ik_panel()
        self._build_fk_panel()
        self._build_trajectory_panel()

    # ──────────────────────────────────────────────────────────────────────────
    # TOGGLE MODE
    # ──────────────────────────────────────────────────────────────────────────
    def toggle_mode(self):
        new = not self.is_digital_twin.get()
        self.is_digital_twin.set(new)
        self.btn_mode.configure(
            text="DIGITAL TWIN: ON" if new else "MODE: VIRTUAL SIM",
            fg_color=BTN_SUCCESS if new else BTN_DEFAULT)

    # ──────────────────────────────────────────────────────────────────────────
    # RENDER LOOP — 50ms (~20 FPS)
    # ──────────────────────────────────────────────────────────────────────────
    def render_loop(self):
        # Digital twin: copy trạng thái từ control_tab
        if self.is_digital_twin.get() and self.control_tab:
            self._tgt_j1 = self.control_tab.j1_angle.get()
            self._tgt_j2 = self.control_tab.j2_angle.get()
            self._tgt_z  = self.control_tab.z_pos.get()

        # Cập nhật workspace rings nếu L1/L2 thay đổi
        self._update_workspace_rings()

        # Lerp khớp xoay (constrained — không đi qua vùng cấm)
        cur_j1 = self.sim_j1.get()
        cur_j2 = self.sim_j2.get()
        cur_z  = self.sim_z.get()

        new_j1 = self._lerp_angle_constrained(
            cur_j1, self._tgt_j1, self.LERP_SPEED, self.J1_MIN, self.J1_MAX)
        new_j2 = self._lerp_angle_constrained(
            cur_j2, self._tgt_j2, self.LERP_SPEED, self.J2_MIN, self.J2_MAX)

        # Normalize về (-180, +180]
        self.sim_j1.set((new_j1 + 180) % 360 - 180)
        self.sim_j2.set((new_j2 + 180) % 360 - 180)

        # Lerp trục Z (tuyến tính)
        self.sim_z.set(self._lerp(cur_z, self._tgt_z, self.LERP_SPEED))

        j1, j2, z = self.sim_j1.get(), self.sim_j2.get(), self.sim_z.get()
        x2, y2, x3, y3 = self._fk(j1, j2)

        # Cập nhật LED + status labels
        in_ws = self._in_workspace(x3, y3)
        self._update_led(in_ws)
        self.lbl_xyz.configure(text=f"X: {x3:.1f} | Y: {y3:.1f} | Z: {z:.1f}")
        self.lbl_joints.configure(text=f"J1: {j1:.1f}° | J2: {j2:.1f}°")

        # Vẽ lại
        self._draw_3d(x2, y2, x3, y3, z)
        self._draw_2d(x2, y2, x3, y3)

        self.after(50, self.render_loop)