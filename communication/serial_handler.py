import serial
import threading
import queue
import time

class SerialHandler:
    """
    Class quản lý giao tiếp Serial an toàn cho Tkinter.
    Sử dụng Queue để truyền dữ liệu từ luồng đọc ngầm lên giao diện chính.
    """
    def __init__(self):
        self.serial_port = serial.Serial()
        self.data_queue = queue.Queue()  # Hàng đợi Thread-safe
        self.is_connected = False
        self.read_thread = None

    def connect(self, port, baudrate=115200):
        """Mở kết nối COM và khởi động luồng đọc ngầm"""
        try:
            self.serial_port.port = port
            self.serial_port.baudrate = baudrate
            self.serial_port.timeout = 0.1 # Timeout nhỏ để không khóa luồng
            self.serial_port.open()
            self.is_connected = True

            # Khởi động luồng đọc dữ liệu độc lập (Daemon thread sẽ tự chết khi đóng app)
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            
            return True, f"Đã kết nối thành công tới {port} ở {baudrate} baud."
        except Exception as e:
            return False, f"Lỗi kết nối: {str(e)}"

    def disconnect(self):
        """Đóng kết nối và dừng luồng đọc"""
        self.is_connected = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
            
        if self.serial_port.is_open:
            self.serial_port.close()

    def send_command(self, cmd):
        """Gửi chuỗi lệnh xuống vi điều khiển STM32"""
        if self.is_connected and self.serial_port.is_open:
            try:
                # Đảm bảo lệnh có ký tự kết thúc (tùy thuộc vào code C trên STM32 của bạn)
                full_cmd = str(cmd) + '\n'
                self.serial_port.write(full_cmd.encode('utf-8'))
                return True
            except Exception as e:
                print(f"Lỗi gửi lệnh: {e}")
                return False
        return False

    def _read_loop(self):
        """
        Vòng lặp ngầm liên tục lắng nghe dữ liệu từ STM32.
        Tuyệt đối không gọi các hàm cập nhật UI (như .set() hay .insert()) ở đây.
        """
        while self.is_connected and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    # Đọc 1 dòng dữ liệu, giải mã và xóa khoảng trắng thừa
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        # Ném dữ liệu thô vào hàng đợi
                        self.data_queue.put(line)
            except Exception:
                # Bỏ qua lỗi ngắt kết nối đột ngột
                pass
            
            # Ngủ một chút để nhường CPU cho luồng giao diện
            time.sleep(0.01) 

    def get_queued_data(self):
        """
        Hàm này sẽ được Tkinter gọi ở luồng chính để lấy dữ liệu ra.
        Trả về một list chứa các dòng tin nhắn nhận được.
        """
        data_list = []
        while not self.data_queue.empty():
            try:
                data_list.append(self.data_queue.get_nowait())
            except queue.Empty:
                break
        return data_list