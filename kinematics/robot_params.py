import math

# ==================== THÔNG SỐ ROBOT ====================
# Chiều dài khâu (mm)
L1 = 100.0
L2 = 100.0

# Hành trình trục Z (Vít me tịnh tiến - mm)
Z_MIN = 0.0
Z_MAX = 300.0

# Giới hạn góc (độ)
Q1_MIN_DEG = -90.0
Q1_MAX_DEG = 90.0
Q2_MIN_DEG = -45.0
Q2_MAX_DEG = 45.0

# Giới hạn góc (rad)
def _deg_to_rad(deg):
    return deg * math.pi / 180.0

Q1_MIN_RAD = _deg_to_rad(Q1_MIN_DEG)
Q1_MAX_RAD = _deg_to_rad(Q1_MAX_DEG)
Q2_MIN_RAD = _deg_to_rad(Q2_MIN_DEG)
Q2_MAX_RAD = _deg_to_rad(Q2_MAX_DEG)

# Vùng làm việc (Mặt phẳng XY)
MAX_REACH = L1 + L2
MIN_REACH = abs(L1 - L2)

# Thông số động cơ
ENCODER_PPR_J1 = 400
ENCODER_PPR_J2 = 400
GEAR_RATIO_J1 = 50
GEAR_RATIO_J2 = 50