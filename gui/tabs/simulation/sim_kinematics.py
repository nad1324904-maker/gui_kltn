# ============================================================================
# gui/tabs/simulation/sim_kinematics.py
# Mixin: helpers toán học, IK/FK solver, lerp, clamp, workspace check
# ============================================================================

import math
from kinematics import inverse_kinematics, rad_to_deg


class SimKinematicsMixin:

    # ──────────────────────────────────────────────────────────────────────────
    # FK đơn giản — trả về tọa độ elbow (x2,y2) và end-effector (x3,y3)
    # ──────────────────────────────────────────────────────────────────────────
    def _fk(self, j1_deg, j2_deg):
        j1r = math.radians(j1_deg)
        j2r = math.radians(j2_deg)
        x2  = self.L1 * math.cos(j1r)
        y2  = self.L1 * math.sin(j1r)
        x3  = x2 + self.L2 * math.cos(j1r + j2r)
        y3  = y2 + self.L2 * math.sin(j1r + j2r)
        return x2, y2, x3, y3

    # ──────────────────────────────────────────────────────────────────────────
    # LERP HELPERS
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _lerp(a, b, t):
        """Nội suy tuyến tính thông thường — dùng cho trục Z"""
        return a + (b - a) * t

    @staticmethod
    def _lerp_angle(current, target, t):
        """Nội suy góc theo đường ngắn nhất, giữ hệ (-180, +180]"""
        diff = (target - current + 180) % 360 - 180
        return current + diff * t

    @staticmethod
    def _lerp_angle_constrained(current, target, t, j_min, j_max):
        """
        Nội suy góc luôn đi qua vùng cho phép [j_min, j_max].
        Vùng cho phép là vùng nhỏ đi qua 0° — ví dụ [-120°, +120°].
        Nếu đường ngắn nhất đi ra ngoài vùng → buộc đi theo chiều trong vùng.
        """
        diff_short = (target - current + 180) % 360 - 180
        diff_long  = diff_short - 360 if diff_short > 0 else diff_short + 360

        mid_short = current + diff_short * 0.5
        mid_long  = current + diff_long  * 0.5

        def in_allowed(angle):
            a = (angle + 180) % 360 - 180
            return j_min <= a <= j_max

        if in_allowed(mid_short):
            diff = diff_short
        elif in_allowed(mid_long):
            diff = diff_long
        else:
            diff = diff_short  # fallback an toàn

        return current + diff * t

    # ──────────────────────────────────────────────────────────────────────────
    # CLAMP & WORKSPACE CHECK
    # ──────────────────────────────────────────────────────────────────────────
    def _clamp_joint(self, j, lo, hi):
        return max(lo, min(hi, j))

    def _in_workspace(self, x, y):
        d = math.sqrt(x**2 + y**2)
        return abs(self.L1 - self.L2) <= d <= (self.L1 + self.L2)

    # ──────────────────────────────────────────────────────────────────────────
    # SET TARGET (bắt đầu lerp animation)
    # ──────────────────────────────────────────────────────────────────────────
    def _set_target(self, j1, j2, z):
        self._tgt_j1 = j1
        self._tgt_j2 = j2
        self._tgt_z  = z

    # ──────────────────────────────────────────────────────────────────────────
    # IK SOLVER
    # ──────────────────────────────────────────────────────────────────────────
    def solve_virtual_ik(self):
        try:
            x = float(self.ent_x.get())
            y = float(self.ent_y.get())
            z = float(self.ent_z_ik.get())
        except ValueError:
            self.lbl_reach.configure(
                text="● Nhập tọa độ hợp lệ!", text_color="#FFA500")
            return

        if not self._in_workspace(x, y):
            self.lbl_reach.configure(
                text="● OUT OF RANGE — Ngoài tầm với!", text_color="#FF4444")
            self.led_canvas.itemconfig(self._led, fill="#FF3333")
            self._ik_solutions = []
            return

        result_up   = inverse_kinematics(x, y, z, self.L1, self.L2, solution='elbow_up')
        result_down = inverse_kinematics(x, y, z, self.L1, self.L2, solution='elbow_down')

        if result_up is None:
            self.lbl_reach.configure(
                text="● IK không có nghiệm!", text_color="#FF4444")
            self._ik_solutions = []
            return

        q1u, q2u, _ = result_up
        self._ik_solutions = [(rad_to_deg(q1u), rad_to_deg(q2u), z)]

        if result_down is not None:
            q1d, q2d, _ = result_down
            self._ik_solutions.append((rad_to_deg(q1d), rad_to_deg(q2d), z))

        self.lbl_reach.configure(text="● IN WORKSPACE", text_color="#1D9E75")
        self._apply_ik_selection()

    def _refresh_ik_preview(self):
        if self._ik_solutions:
            self._apply_ik_selection()

    def _apply_ik_selection(self):
        idx = self.ik_solution.get()
        if idx >= len(self._ik_solutions):
            return
        j1, j2, z = self._ik_solutions[idx]
        if not (self.J1_MIN <= j1 <= self.J1_MAX):
            self.lbl_reach.configure(
                text=f"⚠ J1={j1:.1f}° ngoài giới hạn [{self.J1_MIN:.0f}°, {self.J1_MAX:.0f}°]",
                text_color="#FFA500")
            return
        if not (self.J2_MIN <= j2 <= self.J2_MAX):
            self.lbl_reach.configure(
                text=f"⚠ J2={j2:.1f}° ngoài giới hạn [{self.J2_MIN:.0f}°, {self.J2_MAX:.0f}°]",
                text_color="#FFA500")
            return
        self._set_target(j1, j2, z)

    # ──────────────────────────────────────────────────────────────────────────
    # FK SOLVER
    # ──────────────────────────────────────────────────────────────────────────
    def solve_virtual_fk(self):
        try:
            j1 = float(self.ent_j1.get())
            j2 = float(self.ent_j2.get())
            z  = float(self.ent_sz.get())
        except ValueError:
            return
        if not (self.J1_MIN <= j1 <= self.J1_MAX):
            self.lbl_reach.configure(
                text=f"⚠ J1={j1:.1f}° ngoài giới hạn [{self.J1_MIN:.0f}°, {self.J1_MAX:.0f}°]",
                text_color="#FFA500")
            return
        if not (self.J2_MIN <= j2 <= self.J2_MAX):
            self.lbl_reach.configure(
                text=f"⚠ J2={j2:.1f}° ngoài giới hạn [{self.J2_MIN:.0f}°, {self.J2_MAX:.0f}°]",
                text_color="#FFA500")
            return
        self._set_target(j1, j2, z)