import cv2
import numpy as np

def phan_tich_hinh_dang(frame):
    processed_frame = frame.copy()
    signal = None  
    
    fh, fw, _ = processed_frame.shape
    
    # 1. Thu nhỏ ô quét lại mức 30% cho gọn gàng vừa mắt
    box_size = int(min(fw, fh) * 0.3)
    
    x1 = max(0, int(fw/2 - box_size/2))
    y1 = max(0, int(fh/2 - box_size/2))
    x2 = min(fw, int(fw/2 + box_size/2))
    y2 = min(fh, int(fh/2 + box_size/2))
    
    cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
    cv2.putText(processed_frame, "VUNG QUET", (x1, y1 - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

    roi_mask = np.zeros((fh, fw), dtype=np.uint8)
    cv2.rectangle(roi_mask, (x1, y1), (x2, y2), 255, -1) 

    # 2. Xử lý ảnh
    gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.bitwise_and(mask, mask, mask=roi_mask)
    
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # === ĐIỂM QUYẾT ĐỊNH: TÍNH DIỆN TÍCH TỐI ĐA ===
    roi_area_max = box_size * box_size * 0.9  # Ngưỡng 90% diện tích ô quét
    
    if contours:
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        biggest_contour = contours[0]
        area = cv2.contourArea(biggest_contour)
        
        # CHỈ XÉT KHI: Lớn hơn bụi (1000) VÀ Nhỏ hơn 90% ô quét (Chống nhận nhầm nền)
        if 1000 < area < roi_area_max: 
            peri = cv2.arcLength(biggest_contour, True)
            approx = cv2.approxPolyDP(biggest_contour, 0.04 * peri, True)
            
            bx, by, bw, bh = cv2.boundingRect(approx)
            
            if len(approx) == 4:
                signal = "PASS"
                cv2.drawContours(processed_frame, [approx], -1, (0, 255, 0), 3)
                # Dịch chữ PASS lên cao hơn để không cấn chữ VUNG QUET
                cv2.putText(processed_frame, "PASS: VUONG", (bx, by - 25), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                signal = "FAIL"
                cv2.drawContours(processed_frame, [approx], -1, (0, 0, 255), 3)
                cv2.putText(processed_frame, f"FAIL: {len(approx)} DINH", (bx, by - 25), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            
    return processed_frame, signal