# ============================================================================
# gui/tabs/connection/raspberry_panel.py
# Mixin: toàn bộ logic kết nối Raspberry Pi
# - UI section: _create_camera_section
# - Logic: toggle_camera, _on_webcam_toggle
# ============================================================================

import customtkinter as ctk
import tkinter as tk
from gui.styles import *


class RaspberryPanelMixin:

    # ──────────────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────────────
    def _create_camera_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.grid(row=1, column=1, sticky="nsew",
                   padx=(PADDING_SMALL, PADDING), pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="CAMERA — Raspberry Pi",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(PADDING, PADDING_SMALL))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        # IP
        row_ip = ctk.CTkFrame(content, fg_color="transparent")
        row_ip.pack(fill=tk.X, pady=4)
        ctk.CTkLabel(row_ip, text="Pi IP:", font=FONT_NORMAL,
                     text_color=TEXT_SECONDARY, width=90, anchor="e").pack(side=tk.LEFT)
        self.pi_ip_entry = ctk.CTkEntry(
            row_ip, width=140, placeholder_text="192.168.1.x", font=FONT_NORMAL)
        self.pi_ip_entry.pack(side=tk.LEFT, padx=8)

        # Port
        row_port = ctk.CTkFrame(content, fg_color="transparent")
        row_port.pack(fill=tk.X, pady=4)
        ctk.CTkLabel(row_port, text="Port:", font=FONT_NORMAL,
                     text_color=TEXT_SECONDARY, width=90, anchor="e").pack(side=tk.LEFT)
        self.cam_port_entry = ctk.CTkEntry(row_port, width=80, font=FONT_NORMAL)
        self.cam_port_entry.insert(0, "5000")
        self.cam_port_entry.pack(side=tk.LEFT, padx=8)

        # Checkbox dùng webcam
        self.use_webcam_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            content, text="Dùng Webcam USB (test, không cần Pi)",
            variable=self.use_webcam_var,
            command=self._on_webcam_toggle,
            font=FONT_NORMAL).pack(anchor=tk.W, pady=8)

        # LED trạng thái
        self.camera_led = ctk.CTkLabel(
            content, text="● Chưa kết nối", font=FONT_NORMAL, text_color=TEXT_HINT)
        self.camera_led.pack(anchor=tk.W, pady=(4, 4))

        # Nút bật/tắt camera
        self.cam_btn = ctk.CTkButton(
            content, text="BẬT CAMERA", command=self.toggle_camera,
            fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
            width=200, font=FONT_BUTTON)
        self.cam_btn.pack(pady=4)

    # ──────────────────────────────────────────────────────────────────────────
    # LOGIC
    # ──────────────────────────────────────────────────────────────────────────
    def _on_webcam_toggle(self):
        """Vô hiệu hóa ô IP/Port khi chọn webcam"""
        state = "disabled" if self.use_webcam_var.get() else "normal"
        self.pi_ip_entry.configure(state=state)
        self.cam_port_entry.configure(state=state)

    def toggle_camera(self):
        camera_h = self.main_window.camera

        if not camera_h.is_connected:
            if self.use_webcam_var.get():
                source = 0
            else:
                ip   = self.pi_ip_entry.get().strip()
                port = self.cam_port_entry.get().strip()
                if not ip:
                    self.add_log("ERROR: Nhập IP của Raspberry Pi trước.")
                    return
                source = f"http://{ip}:{port}/video_feed"

            success, msg = camera_h.connect(source)
            self.add_log(msg)
            if success:
                self.cam_btn.configure(
                    text="TẮT CAMERA",
                    fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER)
                self.camera_led.configure(
                    text="● Camera đang chạy", text_color=BTN_SUCCESS)
        else:
            camera_h.disconnect()
            self.cam_btn.configure(
                text="BẬT CAMERA",
                fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER)
            self.camera_led.configure(text="● Chưa kết nối", text_color=TEXT_HINT)
            self.add_log("Camera đã ngắt kết nối.")
