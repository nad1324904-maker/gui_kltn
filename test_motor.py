import serial
import threading
import queue
import customtkinter as ctk
from tkinter import messagebox
import time

class MotorControlGUI:
    def __init__(self):
        self.serial_port = None
        self.is_connected = False
        self.current_encoder = 0
        self.current_rpm = 0
        self.current_speed = 0
        
        # Cấu hình cửa sổ
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("STM32F407 Motor Control with Encoder")
        self.root.geometry("750x650")
        self.root.resizable(False, False)
        
        self.setup_ui()
        self.data_queue = queue.Queue()
        
    def setup_ui(self):
        # Title
        title_label = ctk.CTkLabel(self.root, text="MOTOR CONTROL SYSTEM", 
                                    font=("Arial", 24, "bold"))
        title_label.pack(pady=10)
        
        # Frame kết nối Serial
        serial_frame = ctk.CTkFrame(self.root)
        serial_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(serial_frame, text="COM Port:", font=("Arial", 14)).pack(side="left", padx=10)
        self.com_port_entry = ctk.CTkEntry(serial_frame, width=100)
        self.com_port_entry.pack(side="left", padx=5)
        self.com_port_entry.insert(0, "COM3")
        
        ctk.CTkLabel(serial_frame, text="Baudrate: 115200", font=("Arial", 14)).pack(side="left", padx=10)
        
        self.connect_btn = ctk.CTkButton(serial_frame, text="Connect", command=self.toggle_connection, 
                                         width=100, height=35, font=("Arial", 14))
        self.connect_btn.pack(side="right", padx=10)
        
        # Frame hiển thị encoder
        encoder_frame = ctk.CTkFrame(self.root)
        encoder_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(encoder_frame, text="ENCODER STATUS", font=("Arial", 18, "bold")).pack(pady=5)
        
        enc_value_frame = ctk.CTkFrame(encoder_frame)
        enc_value_frame.pack(pady=10, padx=20, fill="x")
        
        # Pulse count
        pulse_frame = ctk.CTkFrame(enc_value_frame)
        pulse_frame.pack(side="left", padx=20, pady=10, expand=True, fill="x")
        ctk.CTkLabel(pulse_frame, text="Pulse Count:", font=("Arial", 16)).pack()
        self.encoder_label = ctk.CTkLabel(pulse_frame, text="0", font=("Arial", 32, "bold"), text_color="#00FF00")
        self.encoder_label.pack()
        
        # RPM
        rpm_frame = ctk.CTkFrame(enc_value_frame)
        rpm_frame.pack(side="left", padx=20, pady=10, expand=True, fill="x")
        ctk.CTkLabel(rpm_frame, text="RPM:", font=("Arial", 16)).pack()
        self.rpm_label = ctk.CTkLabel(rpm_frame, text="0.0", font=("Arial", 32, "bold"), text_color="#FFFF00")
        self.rpm_label.pack()
        
        # Frame điều khiển động cơ
        motor_frame = ctk.CTkFrame(self.root)
        motor_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(motor_frame, text="MOTOR CONTROL", font=("Arial", 18, "bold")).pack(pady=5)
        
        # Nút điều khiển
        button_frame = ctk.CTkFrame(motor_frame)
        button_frame.pack(pady=10)
        
        self.forward_btn = ctk.CTkButton(button_frame, text="FORWARD", command=self.forward,
                                          fg_color="#00AA00", hover_color="#00FF00",
                                          font=("Arial", 18, "bold"), width=150, height=60)
        self.forward_btn.pack(side="left", padx=10)
        
        self.reverse_btn = ctk.CTkButton(button_frame, text="REVERSE", command=self.reverse,
                                          fg_color="#AA8800", hover_color="#FFCC00",
                                          font=("Arial", 18, "bold"), width=150, height=60)
        self.reverse_btn.pack(side="left", padx=10)
        
        self.stop_btn = ctk.CTkButton(button_frame, text="STOP", command=self.stop,
                                       fg_color="#AA0000", hover_color="#FF0000",
                                       font=("Arial", 18, "bold"), width=150, height=60)
        self.stop_btn.pack(side="left", padx=10)
        
        self.reset_btn = ctk.CTkButton(button_frame, text="RESET", command=self.reset_encoder,
                                        fg_color="#0000AA", hover_color="#0000FF",
                                        font=("Arial", 18, "bold"), width=150, height=60)
        self.reset_btn.pack(side="left", padx=10)
        
        # Thanh trượt tốc độ
        speed_frame = ctk.CTkFrame(motor_frame)
        speed_frame.pack(pady=15, padx=20, fill="x")
        
        ctk.CTkLabel(speed_frame, text="Motor Speed:", font=("Arial", 16, "bold")).pack(side="left", padx=10)
        
        self.speed_slider = ctk.CTkSlider(speed_frame, from_=0, to=100, command=self.change_speed,
                                           width=400, height=25, number_of_steps=100)
        self.speed_slider.pack(side="left", padx=10)
        self.speed_slider.set(0)
        
        self.speed_value_label = ctk.CTkLabel(speed_frame, text="0%", font=("Arial", 20, "bold"), text_color="#00FF00")
        self.speed_value_label.pack(side="left", padx=10)
        
        # Thông tin
        info_frame = ctk.CTkFrame(self.root)
        info_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(info_frame, text="SYSTEM INFORMATION", font=("Arial", 16, "bold")).pack(pady=5)
        
        info_text = """
        • Encoder Resolution: 44 pulses/revolution
        • PWM Frequency: 1kHz
        • Update Rate: 100Hz (10ms)
        • Control: UART at 115200 baud
        """
        ctk.CTkLabel(info_frame, text=info_text, font=("Arial", 12), justify="left").pack(pady=5)
        
        # Status bar
        self.status_label = ctk.CTkLabel(self.root, text="Status: Disconnected", font=("Arial", 13))
        self.status_label.pack(pady=10)
        
    def toggle_connection(self):
        if not self.is_connected:
            try:
                port = self.com_port_entry.get()
                self.serial_port = serial.Serial(port, 115200, timeout=0.1, write_timeout=0.1)
                self.is_connected = True
                self.connect_btn.configure(text="Disconnect", fg_color="#AA0000")
                self.status_label.configure(text="Status: Connected - Reading Encoder", text_color="#00FF00")
                
                # Start threads
                self.read_thread = threading.Thread(target=self.read_serial, daemon=True)
                self.read_thread.start()
                
                self.process_thread = threading.Thread(target=self.process_queue, daemon=True)
                self.process_thread.start()
                
                messagebox.showinfo("Success", f"Connected to {port}")
            except Exception as e:
                messagebox.showerror("Error", f"Cannot connect: {str(e)}")
        else:
            self.is_connected = False
            if self.serial_port:
                self.serial_port.close()
            self.connect_btn.configure(text="Connect", fg_color="#3B8ED0")
            self.status_label.configure(text="Status: Disconnected", text_color="#FF0000")
    
    def read_serial(self):
        buffer = ""
        while self.is_connected:
            try:
                if self.serial_port and self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    buffer += data.decode('utf-8', errors='ignore')
                    
                    lines = buffer.split('\n')
                    buffer = lines[-1]
                    
                    for line in lines[:-1]:
                        line = line.strip()
                        if line:
                            self.data_queue.put(line)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"Read error: {e}")
                time.sleep(0.01)
    
    def process_queue(self):
        while self.is_connected:
            try:
                line = self.data_queue.get_nowait()
                
                if line.startswith("ENC:"):
                    parts = line.split(':')[1].split(',')
                    if len(parts) == 2:
                        encoder_val = int(parts[0])
                        rpm_val = float(parts[1])
                        self.root.after(1, self.update_encoder_display, encoder_val, rpm_val)
                        
                elif line.startswith("OK:"):
                    print(f"Response: {line}")
                    
            except queue.Empty:
                time.sleep(0.01)
            except Exception as e:
                print(f"Process error: {e}")
    
    def update_encoder_display(self, encoder_val, rpm_val):
        self.encoder_label.configure(text=str(encoder_val))
        self.rpm_label.configure(text=f"{rpm_val:.1f}")
    
    def send_command(self, cmd):
        if self.is_connected and self.serial_port:
            try:
                self.serial_port.write(cmd.encode())
                time.sleep(0.05)
            except Exception as e:
                print(f"Send error: {e}")
    
    def send_speed(self, speed):
        if self.is_connected and self.serial_port:
            try:
                speed_str = f"{speed:03d}"
                self.serial_port.write(speed_str.encode())
                time.sleep(0.05)
            except Exception as e:
                print(f"Send speed error: {e}")
    
    def forward(self):
        self.send_command('F')
        time.sleep(0.05)
        self.send_speed(self.current_speed)
        self.status_label.configure(text=f"Status: FORWARD - Speed: {self.current_speed}%", text_color="#00FF00")
    
    def reverse(self):
        self.send_command('B')
        time.sleep(0.05)
        self.send_speed(self.current_speed)
        self.status_label.configure(text=f"Status: REVERSE - Speed: {self.current_speed}%", text_color="#FFFF00")
    
    def stop(self):
        self.send_command('S')
        self.status_label.configure(text="Status: STOPPED", text_color="#FF0000")
    
    def reset_encoder(self):
        self.send_command('R')
        self.current_encoder = 0
        self.current_rpm = 0
        self.root.after(0, self.update_encoder_display, 0, 0)
        messagebox.showinfo("Info", "Encoder reset to 0")
    
    def change_speed(self, value):
        speed_percent = int(value)
        self.current_speed = speed_percent
        self.speed_value_label.configure(text=f"{speed_percent}%")
        self.send_speed(speed_percent)
        self.status_label.configure(text=f"Status: Speed = {speed_percent}%", text_color="#00FF00")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = MotorControlGUI()
    app.run()