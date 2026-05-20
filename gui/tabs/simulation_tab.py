import customtkinter as ctk
import tkinter as tk
import math
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from gui.styles import *
from kinematics import forward_kinematics, inverse_kinematics, deg_to_rad, rad_to_deg
# ──────────────────────────────────────────────────────────────────────────────
# NOTE: Replace these imports with your actual project paths
# from gui.styles import *
# from kinematics import forward_kinematics, inverse_kinematics, deg_to_rad, rad_to_deg
# ══════════════════════════════════════════════════════════════════════════════
class SimulationTab(ctk.CTkFrame):
    """
    Enhanced SCARA PPR Simulation Tab  —  v2
    ────────────────────────────────────────
    Improvements implemented:
      1. Trajectory Planner  – lưu / phát lại waypoints
      2. Reachability Ring   – hiển thị workspace & cảnh báo OOR trực tiếp
      3. Smooth Interpolation – robot di chuyển mượt mà (lerp)
      4. Joint Limit Arcs    – vẽ giới hạn góc J1/J2 trực tiếp trên 3D plot
      5. Overhead 2D View    – mini top-down canvas, elbow-up vs elbow-down
      6. LED Status Dots     – dot indicator màu + tooltip
      7. Enhanced 3D Plot    – grid mờ, floor shadow, end-effector marker
      8. Dual IK Solution    – chọn elbow-up / elbow-down qua radio button
    """

    # ── Cơ học ──────────────────────────────────────────────────────────────
    L1 = 100.0
    L2 = 100.0
    Z_MAX = 200.0

    # Joint limits (degrees)
    J1_MIN, J1_MAX = -150.0, 150.0
    J2_MIN, J2_MAX = -150.0, 150.0

    # Interpolation speed (fraction per frame)
    LERP_SPEED = 0.04

    def __init__(self, parent, main_window=None):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.main_window = main_window
        self.control_tab = None

        # ── Virtual joint state ──
        self.sim_j1   = tk.DoubleVar(value=45.0)
        self.sim_j2   = tk.DoubleVar(value=-90.0)
        self.sim_z    = tk.DoubleVar(value=0.0)

        # ── Interpolation targets ──
        self._tgt_j1 = self.sim_j1.get()
        self._tgt_j2 = self.sim_j2.get()
        self._tgt_z  = self.sim_z.get()

        # ── Digital twin mode ──
        self.is_digital_twin = tk.BooleanVar(value=False)

        # ── IK solution choice ──
        self.ik_solution = tk.IntVar(value=0)   # 0=elbow-up, 1=elbow-down
        self._ik_solutions = []                  # cache both solutions

        # ── Trajectory planner ──
        self.waypoints: list[tuple[float,float,float]] = []
        self._traj_running = False
        self._traj_index   = 0

        self.create_layout()
        self.init_plots()
        self.render_loop()

    # ══════════════════════════════════════════════════════════════════════════
    # LAYOUT
    # ══════════════════════════════════════════════════════════════════════════
    def create_layout(self):
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # ── LEFT: 3D plot ──────────────────────────────────────────────────
        self.frame_3d = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        self.frame_3d.grid(row=0, column=0, sticky="nsew", padx=(0, PADDING_SMALL))

        # ── MIDDLE: 2D top-down view ───────────────────────────────────────
        self.frame_2d = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        self.frame_2d.grid(row=0, column=1, sticky="nsew", padx=(0, PADDING_SMALL))
        ctk.CTkLabel(self.frame_2d, text="TOP VIEW", font=FONT_SECTION,
                     text_color=TEXT_HINT).pack(pady=(8, 0))

        # ── RIGHT: Control panel ───────────────────────────────────────────
        self.right_frame = ctk.CTkScrollableFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        self.right_frame.grid(row=0, column=2, sticky="nsew")

        self._build_status_panel()
        self._build_ik_panel()
        self._build_fk_panel()
        self._build_trajectory_panel()

    # ── Status panel (Feature 6: LED dots) ───────────────────────────────────
    def _build_status_panel(self):
        # Mode button
        self.btn_mode = ctk.CTkButton(
            self.right_frame, text="MODE: VIRTUAL SIM",
            fg_color=BTN_DEFAULT, height=36, font=FONT_BUTTON,
            command=self.toggle_mode)
        self.btn_mode.pack(fill=tk.X, padx=8, pady=(10, 8))

        card = ctk.CTkFrame(self.right_frame, fg_color=BG_CARD)
        card.pack(fill=tk.X, padx=8, pady=4)

        # Title row
        title_row = ctk.CTkFrame(card, fg_color="transparent")
        title_row.pack(fill=tk.X, padx=10, pady=(8, 2))
        ctk.CTkLabel(title_row, text="LIVE STATUS", font=FONT_SECTION).pack(side=tk.LEFT)

        # LED canvas (Feature 6)
        self.led_canvas = tk.Canvas(title_row, width=16, height=16,
                                    bg=BG_CARD, highlightthickness=0)
        self.led_canvas.pack(side=tk.RIGHT, padx=4)
        self._led = self.led_canvas.create_oval(2, 2, 14, 14, fill="#555", outline="")

        # Status labels
        self.lbl_xyz = ctk.CTkLabel(card, text="X: 141.4 | Y: 0.0 | Z: 0.0",
                                    font=FONT_NORMAL, text_color="#00ffcc")
        self.lbl_xyz.pack(pady=2)
        self.lbl_joints = ctk.CTkLabel(card, text="J1: 45.0° | J2: -90.0°",
                                       font=("Segoe UI", 11), text_color=TEXT_HINT)
        self.lbl_joints.pack(pady=(0, 4))

        # Reachability warning (Feature 2)
        self.lbl_reach = ctk.CTkLabel(card, text="● IN WORKSPACE",
                                      font=("Segoe UI", 10, "bold"),
                                      text_color=BTN_SUCCESS)
        self.lbl_reach.pack(pady=(0, 8))

    # ── IK panel (Feature 8: dual solution) ──────────────────────────────────
    def _build_ik_panel(self):
        card = ctk.CTkFrame(self.right_frame, fg_color=BG_CARD)
        card.pack(fill=tk.X, padx=8, pady=6)
        ctk.CTkLabel(card, text="INVERSE KINEMATICS", font=FONT_SECTION).pack(pady=(8,4))

        self.ent_x = self._input_row(card, "Target X (mm):")
        self.ent_y = self._input_row(card, "Target Y (mm):")
        self.ent_z_ik = self._input_row(card, "Target Z (mm):")

        # Elbow selector (Feature 8)
        elbow_row = ctk.CTkFrame(card, fg_color="transparent")
        elbow_row.pack(fill=tk.X, padx=10, pady=4)
        ctk.CTkLabel(elbow_row, text="Elbow:", width=60, anchor="w").pack(side=tk.LEFT)
        ctk.CTkRadioButton(elbow_row, text="Up",   variable=self.ik_solution,
                           value=0, command=self._refresh_ik_preview).pack(side=tk.LEFT, padx=4)
        ctk.CTkRadioButton(elbow_row, text="Down", variable=self.ik_solution,
                           value=1, command=self._refresh_ik_preview).pack(side=tk.LEFT, padx=4)

        ctk.CTkButton(card, text="SOLVE IK & MOVE",
                      fg_color=BTN_PRIMARY, command=self.solve_virtual_ik).pack(
                          pady=(6, 10), padx=16, fill=tk.X)

    # ── FK panel ──────────────────────────────────────────────────────────────
    def _build_fk_panel(self):
        card = ctk.CTkFrame(self.right_frame, fg_color=BG_CARD)
        card.pack(fill=tk.X, padx=8, pady=6)
        ctk.CTkLabel(card, text="FORWARD KINEMATICS", font=FONT_SECTION).pack(pady=(8,4))

        self.ent_j1 = self._input_row(card, "Angle J1 (°):")
        self.ent_j2 = self._input_row(card, "Angle J2 (°):")
        self.ent_sz = self._input_row(card, "Height Z (mm):")

        ctk.CTkButton(card, text="SOLVE FK & MOVE",
                      fg_color="#404060", command=self.solve_virtual_fk).pack(
                          pady=(6, 10), padx=16, fill=tk.X)

    # ── Teaching / Playback panel ─────────────────────────────────────────────
    def _build_trajectory_panel(self):
        card = ctk.CTkFrame(self.right_frame, fg_color=BG_CARD)
        card.pack(fill=tk.X, padx=8, pady=6)
        ctk.CTkLabel(card, text="TEACHING / PLAYBACK", font=FONT_SECTION).pack(pady=(8, 4))

        # ── RECORD: nhập tọa độ ──
        rec_frame = ctk.CTkFrame(card, fg_color="transparent")
        rec_frame.pack(fill=tk.X, padx=10, pady=(0, 4))

        self.ent_teach_x = self._input_row(rec_frame, "X (mm):")
        self.ent_teach_y = self._input_row(rec_frame, "Y (mm):")
        self.ent_teach_z = self._input_row(rec_frame, "Z (mm):")

        ctk.CTkButton(rec_frame, text="+ RECORD POINT",
                      fg_color=BTN_SUCCESS, height=28, font=("Segoe UI", 9, "bold"),
                      command=self.teach_record_point).pack(fill=tk.X, pady=(6, 2))

        # ── Danh sách điểm đã lưu ──
        self.teach_listbox = tk.Listbox(
            card, bg="#0D0D1A", fg="#00ffcc",
            selectbackground="#0F3460",
            font=("Consolas", 9), height=5,
            highlightthickness=0, bd=0)
        self.teach_listbox.pack(fill=tk.X, padx=10, pady=4)

        # Nút xóa điểm / xóa tất cả
        del_row = ctk.CTkFrame(card, fg_color="transparent")
        del_row.pack(fill=tk.X, padx=10, pady=2)
        ctk.CTkButton(del_row, text="✕ XÓA ĐIỂM",
                      fg_color=BTN_DANGER, height=26, font=("Segoe UI", 9, "bold"),
                      command=self.teach_remove_point).pack(side=tk.LEFT, expand=True, padx=(0, 3))
        ctk.CTkButton(del_row, text="🗑 XÓA TẤT CẢ",
                      fg_color="#444", height=26, font=("Segoe UI", 9, "bold"),
                      command=self.teach_clear_all).pack(side=tk.LEFT, expand=True, padx=(3, 0))

        # ── Save / Load ──
        io_row = ctk.CTkFrame(card, fg_color="transparent")
        io_row.pack(fill=tk.X, padx=10, pady=2)
        ctk.CTkButton(io_row, text="💾 SAVE",
                      fg_color=BTN_PRIMARY, height=26, font=("Segoe UI", 9, "bold"),
                      command=self.teach_save).pack(side=tk.LEFT, expand=True, padx=(0, 3))
        ctk.CTkButton(io_row, text="📂 LOAD",
                      fg_color=BTN_DEFAULT, height=26, font=("Segoe UI", 9, "bold"),
                      command=self.teach_load).pack(side=tk.LEFT, expand=True, padx=(3, 0))

        # ── Trạng thái playback ──
        self.lbl_playback_status = ctk.CTkLabel(
            card, text="⏹ Chờ lệnh...",
            font=("Segoe UI", 9), text_color=TEXT_HINT)
        self.lbl_playback_status.pack(pady=(4, 2))

        # ── Start / Stop ──
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

    # ══════════════════════════════════════════════════════════════════════════
    # PLOT INITIALISATION
    # ══════════════════════════════════════════════════════════════════════════
    def init_plots(self):
        self._init_3d_plot()
        self._init_2d_plot()

    # ── 3D plot (Features 4, 7) ────────────────────────────────────────────────
    def _init_3d_plot(self):
        self.fig3d = Figure(figsize=(5, 5), dpi=100, facecolor="#0D0D1A")
        self.ax3d  = self.fig3d.add_subplot(111, projection="3d", facecolor="#0D0D1A")

        ax = self.ax3d
        ax.tick_params(colors="#445566", labelsize=7)
        for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
            pane.fill = False
            pane.set_edgecolor("#223")
        ax.grid(True, color="#1E2A3A", linewidth=0.5, linestyle="--")

        # Robot segments
        self.robot_line,  = ax.plot([], [], [], "o-",
                                    color="#00ffcc", linewidth=3.5, markersize=7,
                                    zorder=5)
        # Floor shadow (Feature 7)
        self.shadow_line, = ax.plot([], [], [],
                                    color="#00884466", linewidth=2, linestyle="--",
                                    zorder=1)
        # End-effector marker (Feature 7)
        self.ee_marker,   = ax.plot([], [], [], "D",
                                    color="#FF6B35", markersize=9, zorder=6)

        # Ghost line for second IK solution (Feature 8)
        self.ghost_line,  = ax.plot([], [], [],
                                    color="#AAAAFF44", linewidth=1.5,
                                    linestyle=":", zorder=3)

        # Joint-limit arcs (Feature 4) – drawn once, updated on resize
        self._arc_j1 = None
        self._arc_j2 = None

        canvas = FigureCanvasTkAgg(self.fig3d, master=self.frame_3d)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.canvas3d = canvas

    # ── 2D top-down plot (Feature 5) ───────────────────────────────────────────
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
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)

        # Workspace rings (Feature 2)
        theta = [i * math.pi/180 for i in range(361)]
        r_max = self.L1 + self.L2
        r_min = abs(self.L1 - self.L2)
        ax.plot([r_max*math.cos(t) for t in theta],
                [r_max*math.sin(t) for t in theta],
                color="#00884466", linewidth=0.8, linestyle="--")
        if r_min > 0:
            ax.plot([r_min*math.cos(t) for t in theta],
                    [r_min*math.sin(t) for t in theta],
                    color="#FF443366", linewidth=0.8, linestyle="--")

        # Robot arm
        self.arm2d_line, = ax.plot([], [], "o-",
                                   color="#00ffcc", linewidth=2, markersize=5)
        # Ghost (second IK solution)
        self.ghost2d,    = ax.plot([], [], ":",
                                   color="#AAAAFF66", linewidth=1.5)
        # EE marker
        self.ee2d,       = ax.plot([], [], "D",
                                   color="#FF6B35", markersize=7)
        # Target cross
        self.target2d,   = ax.plot([], [], "+",
                                   color="#FFDD00", markersize=10, markeredgewidth=1.5)

        canvas = FigureCanvasTkAgg(self.fig2d, master=self.frame_2d)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.canvas2d = canvas

    # ══════════════════════════════════════════════════════════════════════════
    # KINEMATICS HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    def _fk(self, j1_deg, j2_deg):
        j1r = math.radians(j1_deg)
        j2r = math.radians(j2_deg)
        x2  = self.L1 * math.cos(j1r)
        y2  = self.L1 * math.sin(j1r)
        x3  = x2 + self.L2 * math.cos(j1r + j2r)
        y3  = y2 + self.L2 * math.sin(j1r + j2r)
        return x2, y2, x3, y3

    @staticmethod
    def _lerp(a, b, t): return a + (b - a) * t

    @staticmethod
    def _lerp_angle(current, target, t):
        """Tính toán quãng đường ngắn nhất qua vòng tròn 360 độ"""
        # Tìm độ lệch góc ngắn nhất trong khoảng [-180, 180]
        diff = (target - current + 180) % 360 - 180
        
        # Cộng độ lệch này vào vị trí hiện tại
        return current + diff * t
    
    def _clamp_joint(self, j, lo, hi): return max(lo, min(hi, j))

    def _in_workspace(self, x, y):
        d = math.sqrt(x**2 + y**2)
        return abs(self.L1 - self.L2) <= d <= (self.L1 + self.L2)

    # ══════════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ══════════════════════════════════════════════════════════════════════════
    def solve_virtual_ik(self):
        try:
            x = float(self.ent_x.get())
            y = float(self.ent_y.get())
            z = float(self.ent_z_ik.get())
        except ValueError:
            return

        result = inverse_kinematics(x, y, z, self.L1, self.L2)
        if result is None:
            self._set_reach_status(False)
            return

        q1u, q2u, _, q1d, q2d, _ = result
        self._ik_solutions = [
            (rad_to_deg(q1u), rad_to_deg(q2u), z),
            (rad_to_deg(q1d), rad_to_deg(q2d), z),
        ]
        self._set_reach_status(True)
        self._apply_ik_selection()

    def _refresh_ik_preview(self):
        if self._ik_solutions:
            self._apply_ik_selection()

    def _apply_ik_selection(self):
        idx = self.ik_solution.get()
        if idx < len(self._ik_solutions):
            j1, j2, z = self._ik_solutions[idx]
            j1 = self._clamp_joint(j1, self.J1_MIN, self.J1_MAX)
            j2 = self._clamp_joint(j2, self.J2_MIN, self.J2_MAX)
            self._set_target(j1, j2, z)

    def solve_virtual_fk(self):
        try:
            j1 = float(self.ent_j1.get())
            j2 = float(self.ent_j2.get())
            z  = float(self.ent_sz.get())
        except ValueError:
            return
        j1 = self._clamp_joint(j1, self.J1_MIN, self.J1_MAX)
        j2 = self._clamp_joint(j2, self.J2_MIN, self.J2_MAX)
        self._set_target(j1, j2, z)

    def _set_target(self, j1, j2, z):
        """Set interpolation targets (Feature 3)."""
        self._tgt_j1 = j1
        self._tgt_j2 = j2
        self._tgt_z  = z

    def toggle_mode(self):
        new = not self.is_digital_twin.get()
        self.is_digital_twin.set(new)
        self.btn_mode.configure(
            text="DIGITAL TWIN: ON" if new else "MODE: VIRTUAL SIM",
            fg_color=BTN_SUCCESS if new else BTN_DEFAULT)

    # ══════════════════════════════════════════════════════════════════════════
    # TEACHING / PLAYBACK
    # ══════════════════════════════════════════════════════════════════════════

    def teach_record_point(self):
        """Lưu tọa độ từ ô nhập vào danh sách."""
        try:
            x = float(self.ent_teach_x.get())
            y = float(self.ent_teach_y.get())
            z = float(self.ent_teach_z.get())
        except ValueError:
            self.lbl_playback_status.configure(
                text="⚠ Nhập X/Y/Z hợp lệ!", text_color=BTN_WARNING)
            return

        # Kiểm tra tầm với trước khi lưu
        if not self._in_workspace(x, y):
            self.lbl_playback_status.configure(
                text="⚠ Tọa độ ngoài vùng làm việc!", text_color=BTN_DANGER)
            return

        self.waypoints.append((x, y, z))
        idx = len(self.waypoints)
        self.teach_listbox.insert(
            tk.END, f"  P{idx:02d}  X:{x:+7.1f}  Y:{y:+7.1f}  Z:{z:+6.1f}")
        self.lbl_playback_status.configure(
            text=f"✔ Đã lưu P{idx:02d}", text_color=BTN_SUCCESS)

    def teach_remove_point(self):
        """Xóa điểm đang chọn trong listbox."""
        sel = self.teach_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.teach_listbox.delete(idx)
        self.waypoints.pop(idx)
        # Đánh lại số thứ tự
        self._refresh_listbox()
        self.lbl_playback_status.configure(
            text=f"✔ Đã xóa điểm {idx+1}", text_color=TEXT_HINT)

    def teach_clear_all(self):
        """Xóa toàn bộ danh sách điểm."""
        self.waypoints.clear()
        self.teach_listbox.delete(0, tk.END)
        self.lbl_playback_status.configure(
            text="🗑 Đã xóa tất cả điểm", text_color=TEXT_HINT)

    def _refresh_listbox(self):
        """Vẽ lại listbox sau khi xóa để số thứ tự đúng."""
        self.teach_listbox.delete(0, tk.END)
        for i, (x, y, z) in enumerate(self.waypoints):
            self.teach_listbox.insert(
                tk.END, f"  P{i+1:02d}  X:{x:+7.1f}  Y:{y:+7.1f}  Z:{z:+6.1f}")

    def teach_save(self):
        """Lưu danh sách điểm ra file JSON."""
        import json, tkinter.filedialog as fd
        if not self.waypoints:
            self.lbl_playback_status.configure(
                text="⚠ Chưa có điểm nào để lưu!", text_color=BTN_WARNING)
            return
        path = fd.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Lưu danh sách điểm")
        if not path:
            return
        with open(path, "w") as f:
            json.dump(self.waypoints, f, indent=2)
        self.lbl_playback_status.configure(
            text=f"💾 Đã lưu {len(self.waypoints)} điểm", text_color=BTN_SUCCESS)

    def teach_load(self):
        """Tải danh sách điểm từ file JSON."""
        import json, tkinter.filedialog as fd
        path = fd.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Tải danh sách điểm")
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            self.waypoints = [tuple(p) for p in data]
            self._refresh_listbox()
            self.lbl_playback_status.configure(
                text=f"📂 Đã tải {len(self.waypoints)} điểm", text_color=BTN_SUCCESS)
        except Exception as e:
            self.lbl_playback_status.configure(
                text=f"⚠ Lỗi đọc file: {e}", text_color=BTN_DANGER)

    def teach_start(self):
        """Bắt đầu playback: về Home trước, rồi chạy vòng lặp."""
        if not self.waypoints:
            self.lbl_playback_status.configure(
                text="⚠ Chưa có điểm nào!", text_color=BTN_WARNING)
            return
        if self._traj_running:
            return

        self._traj_running = True
        self._traj_index   = 0
        self.btn_play.configure(fg_color=BTN_WARNING, text="▶ ĐANG CHẠY...")

        # Bước 1: về Home (J1=0, J2=0, Z=0)
        self.lbl_playback_status.configure(
            text="🏠 Đang về Home...", text_color=BTN_WARNING)
        self._set_target(0.0, 0.0, 0.0)

        # Chờ 3s để robot mô phỏng di chuyển về home xong rồi mới bắt đầu
        self.after(3000, self._teach_step)

    def _teach_step(self):
        """Chạy tuần tự từng điểm, lặp vô hạn cho đến khi bấm Stop."""
        if not self._traj_running:
            return

        # Hết 1 vòng → quay lại từ đầu (lặp vô hạn)
        if self._traj_index >= len(self.waypoints):
            self._traj_index = 0

        x, y, z = self.waypoints[self._traj_index]
        result = inverse_kinematics(x, y, z, self.L1, self.L2)

        if result:
            j1 = rad_to_deg(result[0])
            j2 = rad_to_deg(result[1])
            self._set_target(j1, j2, z)
            self.lbl_playback_status.configure(
                text=f"▶ P{self._traj_index+1:02d}/{len(self.waypoints):02d}  "
                     f"X:{x:+.1f} Y:{y:+.1f} Z:{z:+.1f}",
                text_color="#00ffcc")
        else:
            self.lbl_playback_status.configure(
                text=f"⚠ P{self._traj_index+1:02d}: ngoài tầm với, bỏ qua",
                text_color=BTN_WARNING)

        self._traj_index += 1
        # Chờ 5s rồi đi điểm tiếp (đủ để lerp animation thấy mượt)
        self.after(5000, self._teach_step)

    def teach_stop(self):
        """Dừng playback."""
        self._traj_running = False
        self._traj_index   = 0
        self.btn_play.configure(fg_color=BTN_PRIMARY, text="▶ START")
        self.lbl_playback_status.configure(
            text="⏹ Đã dừng", text_color=TEXT_HINT)

    # ══════════════════════════════════════════════════════════════════════════
    # RENDER LOOP
    # ══════════════════════════════════════════════════════════════════════════
    def render_loop(self):
        # Digital twin sync
        if self.is_digital_twin.get() and self.control_tab:
            self._tgt_j1 = self.control_tab.j1_angle.get()
            self._tgt_j2 = self.control_tab.j2_angle.get()
            self._tgt_z  = self.control_tab.z_pos.get()

        # Feature 3: smooth interpolation
        cur_j1 = self.sim_j1.get()
        cur_j2 = self.sim_j2.get()
        cur_z  = self.sim_z.get()
        
        # SỬ DỤNG _lerp_angle CHO CÁC KHỚP XOAY (J1, J2)
        self.sim_j1.set(self._lerp_angle(cur_j1, self._tgt_j1, self.LERP_SPEED))
        self.sim_j2.set(self._lerp_angle(cur_j2, self._tgt_j2, self.LERP_SPEED))
        
        # GIỮ NGUYÊN _lerp THƯỜNG CHO TRỤC TỊNH TIẾN (Z)
        self.sim_z.set(self._lerp(cur_z, self._tgt_z, self.LERP_SPEED))

        j1, j2, z = self.sim_j1.get(), self.sim_j2.get(), self.sim_z.get()
        x2, y2, x3, y3 = self._fk(j1, j2)

        # Feature 2: reachability
        in_ws = self._in_workspace(x3, y3)
        self._update_led(in_ws)

        # Update status labels
        self.lbl_xyz.configure(text=f"X: {x3:.1f} | Y: {y3:.1f} | Z: {z:.1f}")
        self.lbl_joints.configure(text=f"J1: {j1:.1f}° | J2: {j2:.1f}°")

        self._draw_3d(x2, y2, x3, y3, z)
        self._draw_2d(x2, y2, x3, y3)
        self.after(50, self.render_loop)   # ~20 fps

    # ── 3D drawing (Features 4, 7) ────────────────────────────────────────────
    def _draw_3d(self, x2, y2, x3, y3, z):
        ax = self.ax3d
        lim = self.L1 + self.L2 + 20

        # Robot arm (base → elbow → wrist at height z)
        self.robot_line.set_data_3d(
            [0, 0, x2, x3],
            [0, 0, y2, y3],
            [0, z, z,  z])

        # Floor shadow (Feature 7)
        self.shadow_line.set_data_3d(
            [0, x2, x3],
            [0, y2, y3],
            [0.5, 0.5, 0.5])

        # End-effector marker (Feature 7)
        self.ee_marker.set_data_3d([x3], [y3], [z])

        # Ghost (second IK solution, Feature 8)
        if len(self._ik_solutions) == 2:
            other_idx = 1 - self.ik_solution.get()
            gj1, gj2, gz = self._ik_solutions[other_idx]
            gx2, gy2, gx3, gy3 = self._fk(gj1, gj2)
            self.ghost_line.set_data_3d(
                [0, gx2, gx3],
                [0, gy2, gy3],
                [gz, gz, gz])
        else:
            self.ghost_line.set_data_3d([], [], [])

        # Feature 4: joint-limit arcs
        self._draw_joint_arcs(ax, z)

        ax.set_xlim([-lim, lim]); ax.set_ylim([-lim, lim])
        ax.set_zlim([0, self.Z_MAX + 20])
        self.canvas3d.draw_idle()

    def _draw_joint_arcs(self, ax, z):
        """Draw arc indicators for J1 and J2 joint limits (Feature 4)."""
        # Remove old arcs
        for attr in ("_arc_j1_line", "_arc_j2_line"):
            old = getattr(self, attr, None)
            if old is not None:
                try: old.remove()
                except: pass

        r1 = self.L1 * 0.85
        angles = [math.radians(a) for a in
                  range(int(self.J1_MIN), int(self.J1_MAX)+1, 3)]
        xa = [r1 * math.cos(a) for a in angles]
        ya = [r1 * math.sin(a) for a in angles]
        za = [z + 2] * len(xa)
        line_j1, = ax.plot(xa, ya, za, color="#FF6B3544",
                           linewidth=1.5, linestyle="-")
        self._arc_j1_line = line_j1

        # J2 arc centred on elbow
        j1r  = math.radians(self.sim_j1.get())
        ex, ey = self.L1 * math.cos(j1r), self.L1 * math.sin(j1r)
        r2   = self.L2 * 0.75
        angles2 = [math.radians(a) for a in
                   range(int(self.J2_MIN), int(self.J2_MAX)+1, 3)]
        xa2 = [ex + r2 * math.cos(j1r + a) for a in angles2]
        ya2 = [ey + r2 * math.sin(j1r + a) for a in angles2]
        za2 = [z + 2] * len(xa2)
        line_j2, = ax.plot(xa2, ya2, za2, color="#AA55FF44",
                           linewidth=1.2, linestyle="-")
        self._arc_j2_line = line_j2

    # ── 2D drawing (Feature 5) ────────────────────────────────────────────────
    def _draw_2d(self, x2, y2, x3, y3):
        self.arm2d_line.set_data([0, x2, x3], [0, y2, y3])
        self.ee2d.set_data([x3], [y3])

        # Ghost second solution (Feature 8)
        if len(self._ik_solutions) == 2:
            other_idx = 1 - self.ik_solution.get()
            gj1, gj2, _ = self._ik_solutions[other_idx]
            gx2, gy2, gx3, gy3 = self._fk(gj1, gj2)
            self.ghost2d.set_data([0, gx2, gx3], [0, gy2, gy3])
        else:
            self.ghost2d.set_data([], [])

        # Target cross: use IK entries if fresh
        if self._ik_solutions:
            idx  = self.ik_solution.get()
            tj1, tj2, _ = self._ik_solutions[idx]
            _, _, tx, ty = self._fk(tj1, tj2)
            self.target2d.set_data([tx], [ty])
        else:
            self.target2d.set_data([], [])

        # Feature 2: colour ring red if OOR
        in_ws = self._in_workspace(x3, y3)
        self.arm2d_line.set_color("#00ffcc" if in_ws else "#FF4444")
        self.canvas2d.draw_idle()

    # ══════════════════════════════════════════════════════════════════════════
    # LED & STATUS HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    def _update_led(self, in_ws: bool):
        color = "#00ff88" if in_ws else "#FF3333"
        self.led_canvas.itemconfig(self._led, fill=color)
        self.lbl_reach.configure(
            text="● IN WORKSPACE" if in_ws else "● OUT OF RANGE",
            text_color=BTN_SUCCESS if in_ws else BTN_DANGER)

    def _set_reach_status(self, ok: bool):
        pass   # LED updated every frame; call here for instant feedback on IK solve

    # ══════════════════════════════════════════════════════════════════════════
    # UI UTILITY
    # ══════════════════════════════════════════════════════════════════════════
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