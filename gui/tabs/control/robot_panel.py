import customtkinter as ctk
import tkinter as tk
from gui.styles import *
from kinematics import (
    deg_to_rad, rad_to_deg,
    forward_kinematics, inverse_kinematics,
    check_reachable
)

class RobotPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        self._create_status_section()
        self._create_jog_section()
        self._create_point_section()

    def _create_status_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="CURRENT STATUS",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        row_xyz = ctk.CTkFrame(content, fg_color="transparent")
        row_xyz.pack(fill=tk.X, pady=2)
        for lbl, var in [("X:", self.controller.x_pos), ("Y:", self.controller.y_pos), ("Z:", self.controller.z_pos)]:
            ctk.CTkLabel(row_xyz, text=lbl, font=FONT_NORMAL,
                         text_color=TEXT_SECONDARY, width=22, anchor="e").pack(side=tk.LEFT)
            ctk.CTkEntry(row_xyz, textvariable=var, width=60,
                         font=FONT_NORMAL, justify="center",
                         state="readonly").pack(side=tk.LEFT, padx=(2, 8))

        row_j = ctk.CTkFrame(content, fg_color="transparent")
        row_j.pack(fill=tk.X, pady=(4, 0))
        for lbl, var in [("θ1:", self.controller.j1_angle), ("θ2:", self.controller.j2_angle)]:
            ctk.CTkLabel(row_j, text=lbl, font=FONT_NORMAL,
                         text_color=TEXT_SECONDARY, width=22, anchor="e").pack(side=tk.LEFT)
            ctk.CTkEntry(row_j, textvariable=var, width=60,
                         font=FONT_NORMAL, justify="center",
                         state="readonly").pack(side=tk.LEFT, padx=(2, 16))

    def _create_jog_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="JOG CONTROL",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        g = ctk.CTkFrame(frame, fg_color="transparent")
        g.pack(padx=PADDING, pady=(0, PADDING))
        g.grid_columnconfigure((0, 1, 2), weight=1)

        for col, text in [(0, "J1  (°)"), (1, "J2  (°)"), (2, "Z  (mm)")]:
            ctk.CTkLabel(g, text=text, font=FONT_SECTION,
                         text_color=TEXT_SECONDARY).grid(row=0, column=col, pady=(0, 2))

        for col, (txt, cmd) in enumerate([
            ("▲  J1+", lambda: self.jog_j1( self.controller.step_size.get())),
            ("▲  J2+", lambda: self.jog_j2( self.controller.step_size.get())),
            ("▲  Z+",  lambda: self.jog_z(  self.controller.step_size_z.get())),
        ]):
            ctk.CTkButton(g, text=txt, width=85,
                          fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
                          command=cmd).grid(row=1, column=col, padx=3, pady=2)

        ctk.CTkEntry(g, textvariable=self.controller.step_size,   width=85, justify="center").grid(row=2, column=0, padx=3, pady=3)
        ctk.CTkEntry(g, textvariable=self.controller.step_size,   width=85, justify="center").grid(row=2, column=1, padx=3, pady=3)
        ctk.CTkEntry(g, textvariable=self.controller.step_size_z, width=85, justify="center").grid(row=2, column=2, padx=3, pady=3)

        for col, (txt, cmd) in enumerate([
            ("▼  J1-", lambda: self.jog_j1(-self.controller.step_size.get())),
            ("▼  J2-", lambda: self.jog_j2(-self.controller.step_size.get())),
            ("▼  Z-",  lambda: self.jog_z( -self.controller.step_size_z.get())),
        ]):
            ctk.CTkButton(g, text=txt, width=85,
                          fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
                          command=cmd).grid(row=3, column=col, padx=3, pady=2)

    def _create_point_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="POINT CONTROL",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        for lbl, var in [("Target X (mm):", self.controller.x_target),
                         ("Target Y (mm):", self.controller.y_target),
                         ("Target Z (mm):", self.controller.z_target)]:
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

    def send_command(self, cmd: str) -> bool:
        serial_h = self.controller.main_window.serial if self.controller.main_window else None
        if serial_h and serial_h.is_connected:
            if serial_h.send_command(cmd):
                self.controller.add_log(f"TX: {cmd}")
                return True
        else:
            self.controller.add_log("Cảnh báo: Chưa kết nối Serial!")
        return False

    def jog_j1(self, delta: float):
        new = round((self.controller.j1_angle.get() + delta) % 360.0, 2)
        self.send_command(f"J1 {new}")
        self.controller.j1_angle.set(new)
        self.update_xy_from_joints()

    def jog_j2(self, delta: float):
        new = round((self.controller.j2_angle.get() + delta) % 360.0, 2)
        self.send_command(f"J2 {new}")
        self.controller.j2_angle.set(new)
        self.update_xy_from_joints()

    def jog_z(self, delta: float):
        new = round(self.controller.z_pos.get() + delta, 2)
        self.send_command(f"Z {new}")
        self.controller.z_pos.set(new)

    def go_to_xy(self):
        x, y, z = self.controller.x_target.get(), self.controller.y_target.get(), self.controller.z_target.get()
        reachable, msg, _ = check_reachable(x, y, z, self.controller.l1, self.controller.l2)
        if not reachable:
            self.controller.add_log(f"ERROR IK: ({x:.1f}, {y:.1f}, {z:.1f}) — {msg}")
            return
        result = inverse_kinematics(x, y, z, self.controller.l1, self.controller.l2, solution='elbow_up')
        if result:
            q1, q2, dz = result
            j1d, j2d   = rad_to_deg(q1), rad_to_deg(q2)
            self.send_command(f"J1 {j1d:.1f}")
            self.send_command(f"J2 {j2d:.1f}")
            self.send_command(f"Z {dz:.1f}")
            self.controller.j1_angle.set(round(j1d, 2))
            self.controller.j2_angle.set(round(j2d, 2))
            self.controller.z_pos.set(round(dz, 2))
            self.update_xy_from_joints()
        else:
            self.controller.add_log(f"ERROR IK: không tìm được nghiệm cho ({x:.1f}, {y:.1f})")

    def go_home(self):
        self.send_command("J1 0")
        self.send_command("J2 0")
        self.send_command("Z 0")
        self.controller.j1_angle.set(0.0)
        self.controller.j2_angle.set(0.0)
        self.controller.z_pos.set(0.0)
        self.update_xy_from_joints()
        self.controller.add_log("→ Home position.")

    def get_position(self):
        self.send_command("GET")

    def update_xy_from_joints(self):
        x, y, z = forward_kinematics(
            deg_to_rad(self.controller.j1_angle.get()),
            deg_to_rad(self.controller.j2_angle.get()),
            self.controller.z_pos.get(),
            self.controller.l1, self.controller.l2
        )
        self.controller.x_pos.set(round(x, 2))
        self.controller.y_pos.set(round(y, 2))
        self.controller.z_pos.set(round(z, 2))