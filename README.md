C:\SCARA_PROJECT
|   main.py                     -> [🖥️ GIAO DIỆN LÕI] File khởi chạy phần mềm.
|   robot_config.json           -> [🤖 STM32] Cấu hình thông số chiều dài tay máy.
|   test_trajectory.json        -> [🤖 STM32] File lưu quỹ đạo test.
|   run_scara.bat               -> [🖥️ GIAO DIỆN LÕI] Lối tắt chạy app trên Desktop.
|   
+---communication               👉 [MODULE GIAO TIẾP MẠNG & PHẦN CỨNG]
|   |   camera_handler.py       -> [📷 XỬ LÝ ẢNH] Logic đọc luồng Video (Stream) từ Pi.
|   |   socket_handler.py       -> [📷 XỬ LÝ ẢNH] Logic TCP/IP Server nhận tín hiệu PASS/FAIL.
|   |   serial_handler.py       -> [🤖 STM32] Logic kết nối cổng COM UART, bóc tách chuỗi.
|   |   
+---gui                         👉 [MODULE GIAO DIỆN CHÍNH]
|   |   main_window.py          -> [🖥️ GIAO DIỆN LÕI] Layout thanh menu bên trái.
|   |   styles.py               -> [🖥️ GIAO DIỆN LÕI] Định nghĩa màu sắc, font chữ chuẩn.
|   |   
|   +---tabs
|   |   |   pid_tuning_tab.py   -> [🤖 STM32] Giao diện tinh chỉnh Kp, Ki, Kd.
|   |   |   settings_tab.py     -> [🖥️ GIAO DIỆN LÕI] Giao diện cài đặt chung.
|   |   |   
|   |   +---connection          👉 [TAB KẾT NỐI]
|   |   |   |   connection_tab.py  -> [🖥️ GIAO DIỆN LÕI] Nơi ghép 2 panel bên dưới lại.
|   |   |   |   raspberry_panel.py -> [📷 XỬ LÝ ẢNH] Khung nhập IP/Port của Camera và Pi.
|   |   |   |   stm32_panel.py     -> [🤖 STM32] Khung chọn cổng COM và Baudrate.
|   |   |   
|   |   +---control             👉 [TAB ĐIỀU KHIỂN ROBOT]
|   |   |   |   control_tab.py     -> [🖥️ GIAO DIỆN LÕI] File lõi, quản lý mode Manual/Auto.
|   |   |   |   camera_panel.py    -> [📷 XỬ LÝ ẢNH] Khung đen hiển thị trực tiếp luồng camera.
|   |   |   |   robot_panel.py     -> [🤖 STM32] Các nút Jog J1, J2, Z và đi tới điểm XYZ.
|   |   |   |   teaching_panel.py  -> [🤖 STM32] Khung lưu điểm Teaching và phát lại (Playback).
|   |   |   |   auto_panel.py      -> [🤝 PHỐI HỢP] Nơi STM32 đợi tín hiệu Vision để gắp vật.
|   |   |   
|   |   +---simulation          👉 [TAB BẢN SAO SỐ DIGITAL TWIN]
|   |   |   |   (Toàn bộ thư mục này thuộc quyền quản lý của người làm 🤖 STM32)
|   |   |   |   simulation_tab.py, sim_kinematics.py, sim_panels.py, sim_plots.py...
|   |   |   
+---kinematics                  👉 [MODULE TOÁN HỌC]
|   |   |   (Toàn bộ thư mục này thuộc quyền quản lý của người làm 🤖 STM32)
|   |   |   kinematic.py        -> [🤖 STM32] Công thức ma trận Động học Thuận/Nghịch (FK/IK).
|   |   
+---pid                         👉 [MODULE DỮ LIỆU PID]
|       pid_data_handler.py     -> [🤖 STM32] Nhận số liệu tốc độ/vị trí từ mạch trả về.
|       
+---plotting                    👉 [MODULE ĐỒ THỊ]
|       real_time_plot.py       -> [🤖 STM32] Vẽ đồ thị hình thang, đồ thị bám vị trí.
|       
\---utils                       
        logger.py               -> [🖥️ GIAO DIỆN LÕI] Ghi nhật ký lỗi (Log) của toàn hệ thống.
