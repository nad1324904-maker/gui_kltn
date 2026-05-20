# ============================================================================
# communication/camera_handler.py
# "Người vận chuyển" frame từ Pi Camera về GUI.
# Tương tự serial_handler.py: tách hoàn toàn logic phần cứng khỏi giao diện.
# ============================================================================

import cv2
import threading
import queue


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

        Args:
            source: int (0, 1, ... cho webcam) hoặc str (URL MJPEG của Pi).
                    Ví dụ: 0  hoặc  "http://192.168.1.10:8080"

        Returns:
            (bool, str): (thành công, thông báo)
        """
        if self.is_connected:
            return False, "Camera đang kết nối. Ngắt kết nối trước."

        cap = cv2.VideoCapture(source)
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

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        if self.cap:
            self.cap.release()
            self.cap = None

        # Xóa hết frame còn trong queue
        while not self.frame_queue.empty():
            self.frame_queue.get_nowait()

    # --------------------------------------------------------------------------
    # PHẦN 2: VÒNG LẶP ĐỌC FRAME (chạy trong thread riêng)
    # --------------------------------------------------------------------------

    def _capture_loop(self):
        """
        Liên tục đọc frame từ camera.
        KHÔNG tương tác với GUI — chỉ đẩy frame vào queue.
        """
        while self._running:
            ret, frame = self.cap.read()

            if not ret:
                # Mất tín hiệu — đặt cờ để GUI biết
                self.is_connected = False
                break

            # Nếu queue đầy, bỏ frame cũ nhất để luôn có frame mới
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass

            self.frame_queue.put(frame)

    # --------------------------------------------------------------------------
    # PHẦN 3: LẤY FRAME (được gọi từ GUI — main thread)
    # --------------------------------------------------------------------------

    def get_frame(self):
        """
        Lấy frame mới nhất từ queue.

        Returns:
            numpy.ndarray (BGR) nếu có frame, None nếu queue rỗng.
        """
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None