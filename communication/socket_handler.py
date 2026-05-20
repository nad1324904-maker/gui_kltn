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
        Khởi tạo TCP Server.
        - host: '0.0.0.0' cho phép nhận kết nối từ mọi IP trong mạng LAN.
        - port: Cổng giao tiếp (phải khớp với code gửi trên Raspberry Pi).
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
        
        # Tạo luồng chạy ngầm để lắng nghe, giải phóng hoàn toàn luồng chính
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        
        # Luồng chính trả về ngay lập tức để giao diện Tkinter được phép render
        return True

    def _listen_loop(self):
        """Vòng lặp ngầm: Mở cổng, chấp nhận kết nối và đọc dữ liệu"""
        # 1. Khởi tạo socket trong luồng ngầm để tránh nghẽn do mạng
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Cho phép sử dụng lại port ngay sau khi tắt (tránh lỗi "Address already in use")
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1) # Chỉ cho phép 1 Pi kết nối
            
            print(f"[SocketHandler] Đã mở TCP Server tại {self.host}:{self.port}. Đang chờ Raspberry Pi...")
            
            # Cài đặt timeout để server không bị treo vĩnh viễn ở lệnh accept()
            self.server_socket.settimeout(1.0)
        except Exception as e:
            print(f"[SocketHandler] LỖI khởi động server mạng: {e}")
            self.is_running = False
            return

        # 2. Vòng lặp lắng nghe và nhận dữ liệu liên tục
        while self.is_running:
            try:
                # Nếu chưa có ai kết nối, đứng chờ ở đây
                if not self.is_connected:
                    try:
                        client, addr = self.server_socket.accept()
                        self.client_socket = client
                        self.is_connected = True
                        print(f"[SocketHandler] Raspberry Pi đã kết nối từ {addr}")
                        
                        # Báo cho GUI biết đã có kết nối
                        self.event_queue.put("CLIENT_CONNECTED")
                    except socket.timeout:
                        continue # Hết 1s không ai kết nối thì quay lại vòng lặp kiểm tra self.is_running
                        
                # Nếu đã có kết nối, liên tục nhận dữ liệu
                if self.is_connected and self.client_socket:
                    try:
                        self.client_socket.settimeout(1.0)
                        data = self.client_socket.recv(1024)
                        
                        if not data:
                            # Nếu data rỗng -> Pi đã ngắt kết nối
                            print("[SocketHandler] Raspberry Pi ngắt kết nối đột ngột.")
                            self._reset_client()
                            continue
                            
                        # Giải mã dữ liệu và dọn dẹp khoảng trắng/kí tự xuống dòng
                        message = data.decode('utf-8').strip().upper()
                        
                        # Chỉ đẩy vào queue nếu đó là lệnh PASS hoặc FAIL
                        if message in ["PASS", "FAIL"]:
                            # Nếu queue đầy, lấy bỏ cái cũ đi
                            if self.signal_queue.full():
                                try:
                                    self.signal_queue.get_nowait()
                                except queue.Empty:
                                    pass
                            self.signal_queue.put(message)
                            
                    except socket.timeout:
                        continue # Pi chưa gửi gì, tiếp tục chờ
                    except Exception as e:
                        print(f"[SocketHandler] Lỗi mất kết nối với Pi: {e}")
                        self._reset_client()

            except Exception as e:
                if self.is_running:
                    print(f"[SocketHandler] Lỗi vòng lặp chính: {e}")
                
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
        """GUI sẽ gọi hàm này định kỳ để lấy tín hiệu vision từ Pi."""
        while True:
            try:
                signal = self.signal_queue.get_nowait()
            except queue.Empty:
                return None

            if signal in ["PASS", "FAIL"]:
                return signal
            # Bỏ qua các tín hiệu trạng thái không phải vision

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
            
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            
        print("[SocketHandler] Đã tắt Server.")

# Dành cho việc test file độc lập
if __name__ == "__main__":
    import time
    server = SocketHandler()
    server.start_server()
    
    try:
        while True:
            sig = server.get_signal()
            if sig:
                print(f"Main thread nhận được: {sig}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        server.stop_server()