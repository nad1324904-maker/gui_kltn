# ============================================================================
# communication/socket_handler.py
# "Cánh cổng" TCP Server nhận tín hiệu Vision (PASS/FAIL) từ Raspberry Pi.
# Chạy trên một luồng (thread) riêng để không làm đơ giao diện CustomTkinter.
# ============================================================================

import socket
import threading
import queue

class SocketHandler:
    def __init__(self, host='0.0.0.0', port=5005):
        """
        Khởi tạo TCP Server lắng nghe tín hiệu phân loại từ Pi.
        """
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        
        self.is_running = False
        self.is_connected = False
        
        # Hàng đợi chứa tín hiệu vision ("PASS" hoặc "FAIL") để GUI lấy ra một cách an toàn
        self.signal_queue = queue.Queue(maxsize=10)
        # Hàng đợi chứa trạng thái kết nối của Pi (CLIENT_CONNECTED / CLIENT_DISCONNECTED)
        self.event_queue = queue.Queue(maxsize=10)
        
        self._thread = None

    def start_server(self):
        """Khởi động luồng ngầm để thiết lập Server và lắng nghe kết nối từ Pi"""
        if self.is_running:
            return True
            
        self.is_running = True
        
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        return True

    def _listen_loop(self):
        """Vòng lặp ngầm: Mở cổng, chấp nhận kết nối và đọc dữ liệu"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1) 
            
            print(f"[SocketHandler] Đã mở TCP Server tại {self.host}:{self.port}. Đang chờ Raspberry Pi...")
            self.server_socket.settimeout(1.0)
        except Exception as e:
            print(f"[SocketHandler] LỖI khởi động server mạng: {e}")
            self.is_running = False
            return

        while self.is_running:
            try:
                # Nếu chưa có Pi nào kết nối, đứng chờ accept
                if not self.is_connected:
                    try:
                        client, addr = self.server_socket.accept()
                        self.client_socket = client
                        self.is_connected = True
                        print(f"[SocketHandler] Raspberry Pi đã kết nối từ {addr}")
                        self.event_queue.put("CLIENT_CONNECTED")
                    except socket.timeout:
                        continue 
                        
                # Nếu đã thông luồng kết nối, tiến hành nhận dữ liệu chuỗi ký tự kết quả
                if self.is_connected and self.client_socket:
                    try:
                        self.client_socket.settimeout(1.0)
                        data = self.client_socket.recv(1024)
                        
                        if not data:
                            print("[SocketHandler] Raspberry Pi chủ động ngắt kết nối.")
                            self._reset_client()
                            continue
                            
                        message = data.decode('utf-8').strip().upper()
                        
                        if message in ["PASS", "FAIL"]:
                            if self.signal_queue.full():
                                try:
                                    self.signal_queue.get_nowait()
                                except queue.Empty:
                                    pass
                            self.signal_queue.put(message)
                            print(f"[SocketHandler] Đã nhận và đẩy vào hàng đợi lệnh: {message}")
                            
                    except socket.timeout:
                        continue 
                    except Exception as e:
                        print(f"[SocketHandler] Lỗi mất kết nối vật lý với Pi: {e}")
                        self._reset_client()

            except Exception as e:
                if self.is_running:
                    print(f"[SocketHandler] Lỗi vòng lặp chính hệ thống: {e}")
                
    def _reset_client(self):
        """Đóng client hiện tại để chờ kết nối mới"""
        self.is_connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except: pass
        self.client_socket = None
        self.event_queue.put("CLIENT_DISCONNECTED")

    def get_signal(self):
        """
        FIX CRITICAL BUG: Loại bỏ vòng lặp vô hạn 'while True' nuốt tín hiệu cũ.
        Mỗi lần hàm này được gọi từ GUI Loop (.after), nó sẽ lấy chính xác 1 lệnh ra xử lý.
        """
        try:
            signal = self.signal_queue.get_nowait()
            if signal in ["PASS", "FAIL"]:
                return signal
        except queue.Empty:
            return None
        return None

    def get_event(self):
        """Lấy các sự kiện kết nối Pi (CLIENT_CONNECTED, CLIENT_DISCONNECTED)."""
        try:
            return self.event_queue.get_nowait()
        except queue.Empty:
            return None

    def stop_server(self):
        """Đóng toàn bộ kết nối và dừng thread"""
        self.is_running = False
        self._reset_client()
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except: pass
            self.server_socket = None
            
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None
            
        print("[SocketHandler] Đã tắt Server hệ thống hoàn toàn.")