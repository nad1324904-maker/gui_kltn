import customtkinter as ctk
import tkinter as tk
from PIL import Image
import cv2
from gui.styles import *

# Gọi Mắt Thần vào đây!
from .vision_utils import phan_tich_hinh_dang

class CameraPanel(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self._create_camera_section()
        self._update_canvas()

    def _create_camera_section(self):
        frame = ctk.CTkFrame(self, fg_color=BG_SECONDARY, corner_radius=8)
        frame.pack(fill=tk.BOTH, expand=True)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill=tk.X, padx=PADDING, pady=(PADDING, 4))
        ctk.CTkLabel(header, text="LIVE CAMERA FEED", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        
        # --- NHÃN BÁO KẾT QUẢ PASS/FAIL ---
        self.vision_result_label = ctk.CTkLabel(header, text="ĐANG QUÉT...", font=("Segoe UI", 16, "bold"), text_color="gray50")
        self.vision_result_label.pack(side=tk.RIGHT, padx=PADDING)

        # ============================================================
        # FIX LỖI PHÌNH TO: Bọc label trong 1 khung bị KHÓA KÍCH THƯỚC
        # ============================================================
        self.cam_container = ctk.CTkFrame(frame, fg_color="black", corner_radius=4)
        self.cam_container.pack(fill=tk.BOTH, expand=True, padx=PADDING, pady=(0, PADDING))
        # Đây là dòng thần chú không cho phần tử con làm phình khung cha
        self.cam_container.pack_propagate(False) 

        # Bỏ cái camera_label vào trong cam_container
        self.camera_label = ctk.CTkLabel(self.cam_container, text="( Chưa kết nối camera )", font=("Segoe UI", 14), text_color="gray50")
        self.camera_label.pack(fill=tk.BOTH, expand=True)

    def _update_canvas(self):
        if hasattr(self.controller, 'main_window') and hasattr(self.controller.main_window, 'camera'):
            cam = self.controller.main_window.camera
            if cam.is_connected:
                frame = cam.get_frame()
                if frame is not None:
                    # Lấy kích thước từ cái Container bị khóa thay vì lấy từ Label
                    w = self.cam_container.winfo_width()
                    h = self.cam_container.winfo_height()
                    
                    # Chờ giao diện load xong khung hình hoàn chỉnh rồi mới xử lý
                    if w > 10 and h > 10:
                        frame = cv2.resize(frame, (w, h))

                        # =========================================
                        # XỬ LÝ ẢNH & IN LOG
                        # =========================================
                        frame, signal = phan_tich_hinh_dang(frame)
                        
                        if not hasattr(self, 'last_test_signal'):
                            self.last_test_signal = None

                        if signal != self.last_test_signal:
                            if signal == "PASS":
                                self.vision_result_label.configure(text="✔ PASS", text_color="#28a745")
                                self.controller.add_log("VISION: Phát hiện Phôi Vuông -> PASS")
                            elif signal == "FAIL":
                                self.vision_result_label.configure(text="✖ FAIL", text_color="#dc3545")
                                self.controller.add_log("VISION: Phôi không hợp lệ -> FAIL")
                            else:
                                self.vision_result_label.configure(text="ĐANG QUÉT...", text_color="gray50")
                            
                            self.last_test_signal = signal

                        # Chuyển ảnh lên GUI bằng kích thước đã ép
                        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        photo = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                        
                        self.camera_label.configure(image=photo, text="")
            else:
                if self.camera_label.cget("text") == "":
                    self.camera_label.configure(image="", text="( Chưa kết nối camera )")
        
        self.after(33, self._update_canvas)