# ============================================================================
# gui/tabs/connection_tab.py
# Tab Kết nối — quản lý Serial (STM32) và Camera (Pi) tập trung.
# Chạy process_serial_queue tại đây vì đây là nơi sở hữu vòng đời kết nối.
# ============================================================================

import customtkinter as ctk
import tkinter as tk
import serial.tools.list_ports
import json
from datetime import datetime

from gui.styles import *


class ConnectionTab(ctk.CTkFrame):

    def __init__(self, parent, main_window=None):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.main_window = main_window

        self._create_layout()
        self.scan_ports()

        # Bắt đầu vòng lặp đọc serial (thread-safe qua after())
        self.process_serial_queue()

    # ============================================================
    # LAYOUT
    # ============================================================
    def _create_layout(self):
        # 2 cột trên: Serial | Camera
        # 1 hàng dưới: System Log
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="CONNECTION MANAGER",
            font=("Segoe UI", 18, "bold"), text_color=TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=PADDING, pady=(PADDING, PADDING_SMALL))

        self._create_serial_section()
        self._create_camera_section()
        self._create_log_section()

    # ============================================================
    # SECTION: SERIAL (STM32)
    # ============================================================
    def _create_serial_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.grid(row=1, column=0, sticky="nsew", padx=(PADDING, PADDING_SMALL), pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="SERIAL — STM32", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(PADDING, PADDING_SMALL)
        )

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        # Cổng COM
        row_com = ctk.CTkFrame(content, fg_color="transparent")
        row_com.pack(fill=tk.X, pady=4)
        ctk.CTkLabel(row_com, text="Cổng COM:", font=FONT_NORMAL,
                     text_color=TEXT_SECONDARY, width=90, anchor="e").pack(side=tk.LEFT)
        self.com_port = ctk.CTkComboBox(row_com, values=["COM1"], width=110)
        self.com_port.pack(side=tk.LEFT, padx=8)
        ctk.CTkButton(row_com, text="⟳", width=32, height=28,
                      fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER,
                      command=self.scan_ports).pack(side=tk.LEFT)

        # Baudrate
        row_baud = ctk.CTkFrame(content, fg_color="transparent")
        row_baud.pack(fill=tk.X, pady=4)
        ctk.CTkLabel(row_baud, text="Baudrate:", font=FONT_NORMAL,
                     text_color=TEXT_SECONDARY, width=90, anchor="e").pack(side=tk.LEFT)
        self.baud_combo = ctk.CTkComboBox(
            row_baud, values=["9600", "57600", "115200", "230400"], width=110
        )
        self.baud_combo.set("115200")
        self.baud_combo.pack(side=tk.LEFT, padx=8)

        # LED trạng thái
        self.serial_led = ctk.CTkLabel(
            content, text="● Chưa kết nối", font=FONT_NORMAL, text_color=TEXT_HINT
        )
        self.serial_led.pack(anchor=tk.W, pady=(10, 4))

        # Nút kết nối / ngắt
        self.connect_btn = ctk.CTkButton(
            content, text="KẾT NỐI", command=self.toggle_serial,
            fg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER,
            width=200, font=FONT_BUTTON
        )
        self.connect_btn.pack(pady=4)

        # E-STOP
        ctk.CTkButton(
            content, text="⚠  E-STOP", command=self.emergency_stop,
            fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
            font=("Segoe UI", 12, "bold"), width=200
        ).pack(pady=(4, 8))

    # ============================================================
    # SECTION: CAMERA (Raspberry Pi)
    # ============================================================
    def _create_camera_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.grid(row=1, column=1, sticky="nsew", padx=(PADDING_SMALL, PADDING), pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="CAMERA — Raspberry Pi", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(PADDING, PADDING_SMALL)
        )

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        # IP
        row_ip = ctk.CTkFrame(content, fg_color="transparent")
        row_ip.pack(fill=tk.X, pady=4)
        ctk.CTkLabel(row_ip, text="Pi IP:", font=FONT_NORMAL,
                     text_color=TEXT_SECONDARY, width=90, anchor="e").pack(side=tk.LEFT)
        self.pi_ip_entry = ctk.CTkEntry(
            row_ip, width=140, placeholder_text="192.168.1.x", font=FONT_NORMAL
        )
        self.pi_ip_entry.pack(side=tk.LEFT, padx=8)

        # Port
        row_port = ctk.CTkFrame(content, fg_color="transparent")
        row_port.pack(fill=tk.X, pady=4)
        ctk.CTkLabel(row_port, text="Port:", font=FONT_NORMAL,
                     text_color=TEXT_SECONDARY, width=90, anchor="e").pack(side=tk.LEFT)
        self.cam_port_entry = ctk.CTkEntry(row_port, width=80, font=FONT_NORMAL)
        self.cam_port_entry.insert(0, "8080")
        self.cam_port_entry.pack(side=tk.LEFT, padx=8)

        # Checkbox dùng webcam (để test khi chưa có Pi)
        self.use_webcam_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            content, text="Dùng Webcam USB (test, không cần Pi)",
            variable=self.use_webcam_var,
            command=self._on_webcam_toggle,
            font=FONT_NORMAL
        ).pack(anchor=tk.W, pady=8)

        # LED trạng thái
        self.camera_led = ctk.CTkLabel(
            content, text="● Chưa kết nối", font=FONT_NORMAL, text_color=TEXT_HINT
        )
        self.camera_led.pack(anchor=tk.W, pady=(4, 4))

        # Nút bật/tắt camera
        self.cam_btn = ctk.CTkButton(
            content, text="BẬT CAMERA", command=self.toggle_camera,
            fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
            width=200, font=FONT_BUTTON
        )
        self.cam_btn.pack(pady=4)

    def _on_webcam_toggle(self):
        """Vô hiệu hóa ô IP/Port khi chọn webcam"""
        state = "disabled" if self.use_webcam_var.get() else "normal"
        self.pi_ip_entry.configure(state=state)
        self.cam_port_entry.configure(state=state)

    # ============================================================
    # SECTION: SYSTEM LOG
    # ============================================================
    def _create_log_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.grid(row=2, column=0, columnspan=2, sticky="nsew",
                   padx=PADDING, pady=(0, PADDING))

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill=tk.X, padx=PADDING, pady=(6, 0))
        ctk.CTkLabel(header, text="SYSTEM LOG", font=FONT_SECTION, text_color=TEXT_SECONDARY).pack(side=tk.LEFT)
        ctk.CTkButton(
            header, text="CLEAR", width=55, height=22,
            command=self.clear_log,
            fg_color=BTN_DEFAULT, hover_color=BTN_DEFAULT_HOVER
        ).pack(side=tk.RIGHT)

        self.log_text = ctk.CTkTextbox(
            frame, height=200, font=FONT_MONO, fg_color=BG_PRIMARY
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=PADDING, pady=(4, PADDING))
    
    # ============================================================
    # SERIAL: scan / kết nối / ngắt
    # ============================================================
    def scan_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            self.com_port.configure(values=ports)
            self.com_port.set(ports[0])
        else:
            self.com_port.configure(values=["Không tìm thấy COM"])
            self.com_port.set("Không tìm thấy COM")

    def toggle_serial(self):
        serial_h  = self.main_window.serial
        settings  = self.main_window.tabs.get("settings")

        if not serial_h.is_connected:
            port = self.com_port.get()
            if port == "Không tìm thấy COM":
                self.add_log("ERROR: Không tìm thấy cổng COM nào.")
                return

            baud = int(self.baud_combo.get())
            success, msg = serial_h.connect(port, baud)
            self.add_log(msg)

            if success:
                self.connect_btn.configure(
                    text="NGẮT KẾT NỐI",
                    fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER
                )
                self.serial_led.configure(text="● Đã kết nối", text_color=BTN_SUCCESS)
                # Dùng after() thay vì sleep() để không đơ GUI
                self.after(500, lambda: self._send_initial_config(settings))
        else:
            serial_h.disconnect()
            self.connect_btn.configure(
                text="KẾT NỐI",
                fg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER
            )
            self.serial_led.configure(text="● Chưa kết nối", text_color=TEXT_HINT)
            self.add_log("Đã ngắt kết nối Serial.")

    def _send_initial_config(self, settings):
        """Gửi toàn bộ thông số cấu hình xuống STM32 ngay sau khi kết nối.
        Dùng after() để gửi tuần tự, không sleep trong main thread."""
        if not settings:
            self.send_command("GET")
            return

        cmds = [
            f"PPR1 {settings.encoder_ppr_j1.get()}",
            f"PPR2 {settings.encoder_ppr_j2.get()}",
            f"PPRD {settings.encoder_ppr_d1.get()}",
            f"GEAR1 {settings.gear_ratio_j1.get()}",
            f"GEAR2 {settings.gear_ratio_j2.get()}",
            f"LEAD {settings.lead_d1.get()}",
            f"DIR1 {settings.dir_j1.get()}",
            f"DIR2 {settings.dir_j2.get()}",
            f"DIRD {settings.dir_d1.get()}",
            f"VMAX1 {settings.vmax_j1.get()}",
            f"VMAX2 {settings.vmax_j2.get()}",
            f"VMAXD {settings.vmax_d1.get()}",
            f"ACC1 {settings.acc_j1.get()}",
            f"ACC2 {settings.acc_j2.get()}",
            f"ACCD {settings.acc_d1.get()}",
            f"PID1 {settings.kp1.get()} {settings.ki1.get()} {settings.kd1.get()}",
            f"PID2 {settings.kp2.get()} {settings.ki2.get()} {settings.kd2.get()}",
            f"PIDD {settings.kp_d1.get()} {settings.ki_d1.get()} {settings.kd_d1.get()}",
            "GET",
        ]
        self._send_cmd_queue(cmds, index=0)

    def _send_cmd_queue(self, cmds, index):
        """Gửi từng lệnh cách nhau 25ms qua after() — không đơ GUI."""
        if index >= len(cmds):
            return
        self.send_command(cmds[index])
        self.after(25, lambda: self._send_cmd_queue(cmds, index + 1))

    def send_command(self, cmd):
        """Gửi lệnh qua serial, ghi log. Trả về True nếu thành công."""
        serial_h = self.main_window.serial
        if serial_h.is_connected:
            if serial_h.send_command(cmd):
                self.add_log(f"TX: {cmd}")
                return True
        else:
            self.add_log("Cảnh báo: Chưa kết nối Serial!")
        return False

    def emergency_stop(self):
        self.send_command("STOP")
        self.add_log("⚠  EMERGENCY STOP ACTIVATED")

    # ============================================================
    # CAMERA: bật / tắt
    # ============================================================
    def toggle_camera(self):
        camera_h = self.main_window.camera

        if not camera_h.is_connected:
            if self.use_webcam_var.get():
                source = 0          # webcam USB index 0
            else:
                ip   = self.pi_ip_entry.get().strip()
                port = self.cam_port_entry.get().strip()
                if not ip:
                    self.add_log("ERROR: Nhập IP của Raspberry Pi trước.")
                    return
                source = f"http://{ip}:{port}"

            success, msg = camera_h.connect(source)
            self.add_log(msg)

            if success:
                self.cam_btn.configure(
                    text="TẮT CAMERA",
                    fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER
                )
                self.camera_led.configure(text="● Camera đang chạy", text_color=BTN_SUCCESS)
        else:
            camera_h.disconnect()
            self.cam_btn.configure(
                text="BẬT CAMERA",
                fg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER
            )
            self.camera_led.configure(text="● Chưa kết nối", text_color=TEXT_HINT)
            self.add_log("Camera đã ngắt kết nối.")

    # ============================================================
    # VÒNG LẶP ĐỌC SERIAL — 50 ms, thread-safe qua after()
    # ============================================================
    def process_serial_queue(self):
        serial_h       = self.main_window.serial
        messages       = serial_h.get_queued_data()
        pid_data_batch = []

        for msg in messages:
            self.add_log(f"RX: {msg}")

            # --- Giao thức JSON (ưu tiên) ---
            if msg.startswith("{"):
                try:
                    data = json.loads(msg)
                    ctrl = self.main_window.tabs.get("control")

                    if ctrl:
                        if "j1" in data and "j2" in data:
                            ctrl.j1_angle.set(data["j1"])
                            ctrl.j2_angle.set(data["j2"])
                            ctrl.update_xy_from_joints()
                        if "z" in data:
                            ctrl.z_pos.set(data["z"])

                    if "t" in data and "sp" in data and "pv" in data:
                        pid_data_batch.append((data["t"], data["sp"], data["pv"]))
                except ValueError:
                    pass

            # --- Giao thức chuỗi cũ (fallback tương thích ngược) ---
            elif msg.startswith("POS"):
                parts = msg.split()
                if len(parts) >= 3:
                    ctrl = self.main_window.tabs.get("control")
                    if ctrl:
                        ctrl.j1_angle.set(float(parts[1]))
                        ctrl.j2_angle.set(float(parts[2]))
                        ctrl.update_xy_from_joints()

            elif msg.startswith("DATA"):
                pid_tab = self.main_window.tabs.get("pid")
                if pid_tab and hasattr(pid_tab, "process_real_time_data"):
                    pid_tab.process_real_time_data(msg)

        # Gửi batch PID sang tab biểu đồ
        if pid_data_batch:
            pid_tab = self.main_window.tabs.get("pid")
            if pid_tab and hasattr(pid_tab, "add_data_batch"):
                pid_tab.add_data_batch(pid_data_batch)

        self.after(50, self.process_serial_queue)

    # ============================================================
    # LOG
    # ============================================================
    def add_log(self, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {message}\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)
        self.add_log("Log cleared.")