# ============================================================================
# gui/tabs/simulation/sim_plots.py
# Mixin: khởi tạo và vẽ lại 3D/2D Matplotlib plots
# ============================================================================

import math
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk


class SimPlotsMixin:

    # ──────────────────────────────────────────────────────────────────────────
    # KHỞI TẠO
    # ──────────────────────────────────────────────────────────────────────────
    def init_plots(self):
        self._init_3d_plot()
        self._init_2d_plot()

    def _init_3d_plot(self):
        self.fig3d = Figure(figsize=(5, 5), dpi=100, facecolor="#0D0D1A")
        self.ax3d  = self.fig3d.add_subplot(111, projection="3d", facecolor="#0D0D1A")

        ax = self.ax3d
        ax.tick_params(colors="#445566", labelsize=7)
        for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
            pane.fill = False
            pane.set_edgecolor("#223")
        ax.grid(True, color="#1E2A3A", linewidth=0.5, linestyle="--")

        self.robot_line,  = ax.plot([], [], [], "o-",
                                    color="#00ffcc", linewidth=3.5, markersize=7, zorder=5)
        self.shadow_line, = ax.plot([], [], [],
                                    color="#00884466", linewidth=2, linestyle="--", zorder=1)
        self.ee_marker,   = ax.plot([], [], [], "D",
                                    color="#FF6B35", markersize=9, zorder=6)
        self.ghost_line,  = ax.plot([], [], [],
                                    color="#AAAAFF44", linewidth=1.5, linestyle=":", zorder=3)

        self._arc_j1_line = None
        self._arc_j2_line = None

        canvas = FigureCanvasTkAgg(self.fig3d, master=self.frame_3d)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.canvas3d = canvas

    def _init_2d_plot(self):
        self.fig2d = Figure(figsize=(2.5, 2.5), dpi=90, facecolor="#0D0D1A")
        self.ax2d  = self.fig2d.add_subplot(111, facecolor="#0D0D1A")

        ax = self.ax2d
        ax.set_aspect("equal")
        ax.tick_params(colors="#445566", labelsize=6)
        ax.spines[:].set_color("#223344")
        ax.grid(True, color="#1E2A3A", linewidth=0.4, linestyle="--")
        ax.set_xlabel("X", color="#667788", fontsize=7)
        ax.set_ylabel("Y", color="#667788", fontsize=7)

        lim = self.L1 + self.L2 + 20
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)

        # Workspace rings — Line2D để cập nhật động
        theta = [i * math.pi / 180 for i in range(361)]
        self._ws_theta = theta
        r_max = self.L1 + self.L2
        r_min = abs(self.L1 - self.L2)

        self.ws_ring_max, = ax.plot(
            [r_max * math.cos(t) for t in theta],
            [r_max * math.sin(t) for t in theta],
            color="#00884466", linewidth=0.8, linestyle="--")
        self.ws_ring_min, = ax.plot(
            [r_min * math.cos(t) for t in theta] if r_min > 0 else [],
            [r_min * math.sin(t) for t in theta] if r_min > 0 else [],
            color="#FF443366", linewidth=0.8, linestyle="--")

        self.arm2d_line, = ax.plot([], [], "o-", color="#00ffcc", linewidth=2, markersize=5)
        self.ghost2d,    = ax.plot([], [], ":", color="#AAAAFF66", linewidth=1.5)
        self.ee2d,       = ax.plot([], [], "D", color="#FF6B35", markersize=7)
        self.target2d,   = ax.plot([], [], "+", color="#FFDD00", markersize=10, markeredgewidth=1.5)

        canvas = FigureCanvasTkAgg(self.fig2d, master=self.frame_2d)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.canvas2d = canvas

    # ──────────────────────────────────────────────────────────────────────────
    # CẬP NHẬT WORKSPACE RINGS (gọi mỗi frame)
    # ──────────────────────────────────────────────────────────────────────────
    def _update_workspace_rings(self):
        theta = self._ws_theta
        r_max = self.L1 + self.L2
        r_min = abs(self.L1 - self.L2)
        self.ws_ring_max.set_data(
            [r_max * math.cos(t) for t in theta],
            [r_max * math.sin(t) for t in theta])
        if r_min > 0:
            self.ws_ring_min.set_data(
                [r_min * math.cos(t) for t in theta],
                [r_min * math.sin(t) for t in theta])
        lim = r_max + 20
        self.ax2d.set_xlim(-lim, lim)
        self.ax2d.set_ylim(-lim, lim)

    # ──────────────────────────────────────────────────────────────────────────
    # VẼ 3D (gọi mỗi frame)
    # ──────────────────────────────────────────────────────────────────────────
    def _draw_3d(self, x2, y2, x3, y3, z):
        ax  = self.ax3d
        lim = self.L1 + self.L2 + 20

        self.robot_line.set_data_3d(
            [0, 0, x2, x3],
            [0, 0, y2, y3],
            [0, z,  z,  z])
        self.shadow_line.set_data_3d(
            [0, x2, x3],
            [0, y2, y3],
            [0.5, 0.5, 0.5])
        self.ee_marker.set_data_3d([x3], [y3], [z])

        # Ghost — nghiệm IK còn lại
        if len(self._ik_solutions) == 2:
            other_idx = 1 - self.ik_solution.get()
            gj1, gj2, gz = self._ik_solutions[other_idx]
            gx2, gy2, gx3, gy3 = self._fk(gj1, gj2)
            self.ghost_line.set_data_3d([0, gx2, gx3], [0, gy2, gy3], [gz, gz, gz])
        else:
            self.ghost_line.set_data_3d([], [], [])

        self._draw_joint_arcs(ax, z)

        ax.set_xlim([-lim, lim])
        ax.set_ylim([-lim, lim])
        ax.set_zlim([0, self.Z_MAX + 20])
        self.canvas3d.draw_idle()

    def _draw_joint_arcs(self, ax, z):
        """Vẽ cung giới hạn J1 và J2 trên 3D plot"""
        for attr in ("_arc_j1_line", "_arc_j2_line"):
            old = getattr(self, attr, None)
            if old is not None:
                try:
                    old.remove()
                except Exception:
                    pass

        # Cung J1
        r1     = self.L1 * 0.85
        angles = [math.radians(a) for a in range(int(self.J1_MIN), int(self.J1_MAX) + 1, 3)]
        xa     = [r1 * math.cos(a) for a in angles]
        ya     = [r1 * math.sin(a) for a in angles]
        line_j1, = ax.plot(xa, ya, [z + 2] * len(xa),
                           color="#FF6B3544", linewidth=1.5)
        self._arc_j1_line = line_j1

        # Cung J2 — tâm tại elbow
        j1r    = math.radians(self.sim_j1.get())
        ex, ey = self.L1 * math.cos(j1r), self.L1 * math.sin(j1r)
        r2     = self.L2 * 0.75
        angles2 = [math.radians(a) for a in range(int(self.J2_MIN), int(self.J2_MAX) + 1, 3)]
        xa2    = [ex + r2 * math.cos(j1r + a) for a in angles2]
        ya2    = [ey + r2 * math.sin(j1r + a) for a in angles2]
        line_j2, = ax.plot(xa2, ya2, [z + 2] * len(xa2),
                           color="#AA55FF44", linewidth=1.2)
        self._arc_j2_line = line_j2

    # ──────────────────────────────────────────────────────────────────────────
    # VẼ 2D TOP VIEW (gọi mỗi frame)
    # ──────────────────────────────────────────────────────────────────────────
    def _draw_2d(self, x2, y2, x3, y3):
        self.arm2d_line.set_data([0, x2, x3], [0, y2, y3])
        self.ee2d.set_data([x3], [y3])

        if len(self._ik_solutions) == 2:
            other_idx = 1 - self.ik_solution.get()
            gj1, gj2, _ = self._ik_solutions[other_idx]
            gx2, gy2, gx3, gy3 = self._fk(gj1, gj2)
            self.ghost2d.set_data([0, gx2, gx3], [0, gy2, gy3])
        else:
            self.ghost2d.set_data([], [])

        if self._ik_solutions:
            idx = self.ik_solution.get()
            tj1, tj2, _ = self._ik_solutions[idx]
            _, _, tx, ty = self._fk(tj1, tj2)
            self.target2d.set_data([tx], [ty])
        else:
            self.target2d.set_data([], [])

        in_ws = self._in_workspace(x3, y3)
        self.arm2d_line.set_color("#00ffcc" if in_ws else "#FF4444")
        self.canvas2d.draw_idle()