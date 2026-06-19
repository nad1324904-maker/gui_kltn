# ============================================================================
# communication/camera_handler.py
# "Người vận chuyển" frame từ Pi Camera về GUI.
# Tương tự serial_handler.py: tách hoàn toàn logic phần cứng khỏi giao diện.
# ============================================================================

import cv2
import threading
import queue
import time


class CameraHandler:
    """
    Quản lý kết nối và đọc frame từ nguồn camera (MJPEG stream hoặc webcam).
    Chạy trong thread riêng, đẩy frame vào queue để GUI lấy một cách thread-safe.
    """

    def __init__(self):
        self.cap = None
        self.is_connected = False
        self._running = False
        self._thread = None

        # Queue chứa frame mới nhất. maxsize=2 để tránh tích lũy frame cũ,
        # đảm bảo GUI luôn hiển thị ảnh gần thật nhất.
        self.frame_queue = queue.Queue(maxsize=2)

    # --------------------------------------------------------------------------
    # PHẦN 1: KẾT NỐI / NGẮT KẾT NỐI
    # --------------------------------------------------------------------------

    def connect(self, source):
        """
        Kết nối tới nguồn camera.
        """
        if self.is_connected:
            return False, "Camera đang kết nối. Ngắt kết nối trước."

        cap = cv2.VideoCapture(source)
        # Ép buffer về 1 để tránh độ trễ tích lũy trên cáp LAN mạng dây
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            return False, f"ERROR: Không mở được nguồn camera: {source}"

        self.cap = cap
        self.is_connected = True
        self._running = True

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        label = f"webcam (index={source})" if isinstance(source, int) else source
        return True, f"Camera connected: {label}"

    def disconnect(self):
        """Dừng thread và giải phóng camera."""
        self._running = False
        self.is_connected = False

        # FIX CRITICAL BUG: Giải phóng cap TRƯỚC khi join thread để bẻ gãy lệnh cap.read() đang bị block ngầm nếu đứt mạng
        if self.cap:
            self.cap.release()
            self.cap = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None

        # Xóa hết frame tồn đọng còn trong queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

    # --------------------------------------------------------------------------
    # PHẦN 2: VÒNG LẶP ĐỌC FRAME (chạy trong thread riêng)
    # --------------------------------------------------------------------------

    def _capture_loop(self):
        """
        Liên tục đọc frame từ camera.
        KHÔNG tương tác với GUI — chỉ đẩy frame vào queue.
        """
        while self._running and self.cap:
            try:
                ret, frame = self.cap.read()

                if not ret:
                    # Mất tín hiệu mạng hoặc đóng camera bên phía Pi
                    self.is_connected = False
                    break

                # Nếu queue đầy, chủ động giải phóng ảnh cũ nhất để nhét ảnh mới thời gian thực vào
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass

                if self._running:
                    self.frame_queue.put(frame)
            except Exception:
                self.is_connected = False
                break
                
        self.is_connected = False

    # --------------------------------------------------------------------------
    # PHẦN 3: LẤY FRAME (được gọi từ GUI — main thread định kỳ)
    # --------------------------------------------------------------------------

    def get_frame(self):
        """
        Lấy frame mới nhất từ queue.
        """
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None