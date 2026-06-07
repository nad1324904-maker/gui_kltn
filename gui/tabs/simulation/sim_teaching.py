# ============================================================================
# gui/tabs/simulation/sim_teaching.py
# Mixin: Teaching / Playback — record, save, load, play, stop
# ============================================================================

import json
import tkinter as tk
import tkinter.filedialog as fd
from kinematics import inverse_kinematics, rad_to_deg


class SimTeachingMixin:

    def teach_record_point(self):
        """Lưu tọa độ từ ô nhập vào danh sách waypoints"""
        try:
            x = float(self.ent_teach_x.get())
            y = float(self.ent_teach_y.get())
            z = float(self.ent_teach_z.get())
        except ValueError:
            self.lbl_playback_status.configure(
                text="⚠ Nhập X/Y/Z hợp lệ!", text_color="#FFA500")
            return

        if not self._in_workspace(x, y):
            self.lbl_playback_status.configure(
                text="⚠ Tọa độ ngoài vùng làm việc!", text_color="#FF4444")
            return

        self.waypoints.append((x, y, z))
        idx = len(self.waypoints)
        self.teach_listbox.insert(
            tk.END, f"  P{idx:02d}  X:{x:+7.1f}  Y:{y:+7.1f}  Z:{z:+6.1f}")
        self.lbl_playback_status.configure(
            text=f"✔ Đã lưu P{idx:02d}", text_color="#1D9E75")

    def teach_remove_point(self):
        """Xóa điểm đang chọn trong listbox"""
        sel = self.teach_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.teach_listbox.delete(idx)
        self.waypoints.pop(idx)
        self._refresh_listbox()
        self.lbl_playback_status.configure(
            text=f"✔ Đã xóa điểm {idx + 1}", text_color="#667788")

    def teach_clear_all(self):
        """Xóa toàn bộ danh sách"""
        self.waypoints.clear()
        self.teach_listbox.delete(0, tk.END)
        self.lbl_playback_status.configure(
            text="🗑 Đã xóa tất cả điểm", text_color="#667788")

    def _refresh_listbox(self):
        """Vẽ lại listbox sau khi xóa để số thứ tự đúng"""
        self.teach_listbox.delete(0, tk.END)
        for i, (x, y, z) in enumerate(self.waypoints):
            self.teach_listbox.insert(
                tk.END, f"  P{i + 1:02d}  X:{x:+7.1f}  Y:{y:+7.1f}  Z:{z:+6.1f}")

    def teach_save(self):
        """Lưu danh sách điểm ra file JSON"""
        if not self.waypoints:
            self.lbl_playback_status.configure(
                text="⚠ Chưa có điểm nào để lưu!", text_color="#FFA500")
            return
        path = fd.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Lưu danh sách điểm")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.waypoints, f, indent=2)
            self.lbl_playback_status.configure(
                text=f"💾 Đã lưu {len(self.waypoints)} điểm", text_color="#1D9E75")
        except Exception as e:
            self.lbl_playback_status.configure(
                text=f"⚠ Lỗi lưu file: {e}", text_color="#FF4444")

    def teach_load(self):
        """Tải danh sách điểm từ file JSON"""
        path = fd.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Tải danh sách điểm")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("File JSON phải là một danh sách.")
            self.waypoints = [tuple(pt) for pt in data]
            self._refresh_listbox()
            self.lbl_playback_status.configure(
                text=f"📂 Đã tải {len(self.waypoints)} điểm", text_color="#1D9E75")
        except (json.JSONDecodeError, ValueError) as e:
            self.lbl_playback_status.configure(
                text=f"⚠ File không hợp lệ: {e}", text_color="#FF4444")

    def teach_start(self):
        """Bắt đầu playback từ điểm đầu tiên"""
        if not self.waypoints:
            self.lbl_playback_status.configure(
                text="⚠ Chưa có điểm nào!", text_color="#FFA500")
            return
        self._traj_running = True
        self._traj_index   = 0
        self.btn_play.configure(fg_color="#FF4444", text="■ STOP")
        # Về Home trước, sau 3s bắt đầu chạy
        self._set_target(0, 0, 0)
        self.after(3000, self._teach_step)

    def _teach_step(self):
        """Gửi từng waypoint cách nhau 5s — không dùng while True"""
        if not self._traj_running:
            return

        if self._traj_index >= len(self.waypoints):
            self._traj_index = 0  # lặp vô hạn

        x, y, z   = self.waypoints[self._traj_index]
        result     = inverse_kinematics(x, y, z, self.L1, self.L2)

        if result:
            j1, j2, _ = result
            j1 = rad_to_deg(j1)
            j2 = rad_to_deg(j2)
            self._set_target(j1, j2, z)
            self.lbl_playback_status.configure(
                text=f"▶ P{self._traj_index + 1:02d}/{len(self.waypoints):02d}  "
                     f"X:{x:+.1f} Y:{y:+.1f} Z:{z:+.1f}",
                text_color="#00ffcc")
        else:
            self.lbl_playback_status.configure(
                text=f"⚠ P{self._traj_index + 1:02d}: ngoài tầm với, bỏ qua",
                text_color="#FFA500")

        self._traj_index += 1
        self.after(5000, self._teach_step)

    def teach_stop(self):
        """Dừng playback"""
        self._traj_running = False
        self._traj_index   = 0
        self.btn_play.configure(fg_color="#0F3460", text="▶ START")
        self.lbl_playback_status.configure(text="⏹ Đã dừng", text_color="#667788")