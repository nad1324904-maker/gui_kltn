import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import cv2
from gui.styles import *

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
        ctk.CTkLabel(header, text="LIVE CAMERA FEED",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(side=tk.LEFT)
        ctk.CTkLabel(header, text="(Kết nối tại tab Kết nối)",
                     font=("Segoe UI", 9), text_color=TEXT_HINT).pack(side=tk.LEFT, padx=8)

        self.camera_label = ctk.CTkLabel(
            frame,
            text="( Chưa kết nối camera )\nVào tab 'Kết nối' để bật camera.",
            font=FONT_NORMAL, text_color=TEXT_HINT,
            fg_color="black", corner_radius=4
        )
        self.camera_label.pack(fill=tk.BOTH, expand=True, padx=PADDING, pady=(0, PADDING))

    def _update_canvas(self):
        if self.controller.main_window:
            cam = self.controller.main_window.camera
            if cam.is_connected:
                frame = cam.get_frame()
                if frame is not None:
                    w = self.camera_label.winfo_width()
                    h = self.camera_label.winfo_height()
                    if w > 1 and h > 1:
                        frame = cv2.resize(frame, (w, h))
                    img   = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    photo = ImageTk.PhotoImage(img)
                    self.camera_label.configure(image=photo, text="")
                    self.camera_label.image = photo  
            else:
                if self.camera_label.cget("text") == "":
                    self.camera_label.configure(
                        image=None,
                        text="( Chưa kết nối camera )\nVào tab 'Kết nối' để bật camera."
                    )
        self.after(33, self._update_canvas)