import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
from gui.styles import *

class TeachingPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

        self.teach_points   = []
        self.playback_index = 0
        self.is_playing     = False

        self._create_teaching_section()

    def _create_teaching_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.X, pady=(0, PADDING_SMALL))

        ctk.CTkLabel(frame, text="TEACHING / PLAYBACK",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(
            anchor=tk.W, padx=PADDING, pady=(8, 4))

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.pack(fill=tk.X, padx=PADDING, pady=(0, PADDING))

        list_frame = ctk.CTkFrame(content, fg_color=BG_PRIMARY, corner_radius=4)
        list_frame.pack(fill=tk.X, pady=(0, 8))

        self.teach_listbox = tk.Listbox(
            list_frame, height=5,
            bg=BG_PRIMARY, fg=TEXT_PRIMARY,
            selectbackground=BTN_PRIMARY,
            font=("Consolas", 10), bd=0, highlightthickness=0
        )
        self.teach_listbox.pack(fill=tk.X, padx=4, pady=4)

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

    def _teach_current_pos(self):
        pt = (round(self.controller.j1_angle.get(), 2),
              round(self.controller.j2_angle.get(), 2),
              round(self.controller.z_pos.get(), 2))
        self.teach_points.append(pt)
        idx = len(self.teach_points)
        self.teach_listbox.insert(tk.END,
            f"P{idx:02d}  J1={pt[0]:7.2f}°  J2={pt[1]:7.2f}°  Z={pt[2]:6.2f}mm")
        self.controller.add_log(f"Teach P{idx:02d}: J1={pt[0]}, J2={pt[1]}, Z={pt[2]}")

    def _delete_teach_point(self):
        sel = self.teach_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.teach_listbox.delete(idx)
        self.teach_points.pop(idx)
        self.controller.add_log(f"Đã xóa điểm P{idx+1:02d}.")

    def _clear_teach_points(self):
        if not self.teach_points:
            return
        if messagebox.askyesno("Xác nhận", "Xóa toàn bộ điểm đã dạy?"):
            self.teach_points.clear()
            self.teach_listbox.delete(0, tk.END)
            self.controller.add_log("Đã xóa toàn bộ teach points.")

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
            self.controller.add_log(f"Đã lưu {len(data)} điểm → {os.path.basename(path)}")
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
            self.controller.add_log(f"Nạp {len(waypoints)} điểm từ {os.path.basename(path)}")
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
            self.controller.add_log(f"Bắt đầu playback {len(self.teach_points)} điểm...")
            self._playback_tick()
        else:
            self.is_playing = False
            self.play_btn.configure(text="▶  PLAY TRAJECTORY", fg_color=BTN_SUCCESS)
            self.controller.add_log("Playback đã dừng.")

    def _playback_tick(self):
        if not self.is_playing or self.playback_index >= len(self.teach_points):
            self.is_playing = False
            self.play_btn.configure(text="▶  PLAY TRAJECTORY", fg_color=BTN_SUCCESS)
            self.controller.add_log("Playback hoàn thành.")
            return
        pt = self.teach_points[self.playback_index]
        self.controller.robot_panel.send_command(f"J1 {pt[0]}")
        self.controller.robot_panel.send_command(f"J2 {pt[1]}")
        self.controller.robot_panel.send_command(f"Z {pt[2]}")
        
        self.controller.j1_angle.set(pt[0])
        self.controller.j2_angle.set(pt[1])
        self.controller.z_pos.set(pt[2])
        self.controller.robot_panel.update_xy_from_joints()
        
        self.controller.add_log(f"Playback P{self.playback_index+1:02d}: J1={pt[0]}, J2={pt[1]}, Z={pt[2]}")
        self.playback_index += 1
        self.after(500, self._playback_tick)