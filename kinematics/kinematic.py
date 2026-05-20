"""
kinematic.py - Các hàm tính toán động học robot SCARA PRR (3D)
"""

import math
import numpy as np

def deg_to_rad(deg):
    """Chuyển độ sang radian"""
    return deg * math.pi / 180.0

def rad_to_deg(rad):
    """Chuyển radian sang độ"""
    return rad * 180.0 / math.pi

def forward_kinematics(q1_rad, q2_rad, d1_z, l1, l2):
    """
    Động học thuận robot SCARA PRR (3D)
    Trả về tọa độ (x, y, z) của điểm cuối (mm)
    """
    x = l1 * math.cos(q1_rad) + l2 * math.cos(q1_rad + q2_rad)
    y = l1 * math.sin(q1_rad) + l2 * math.sin(q1_rad + q2_rad)
    z = d1_z # Trục Z độc lập bằng chính độ dịch d1
    return x, y, z

def inverse_kinematics(x, y, z, l1, l2, solution='elbow_up'):
    """
    Động học ngược robot SCARA PRR (3D)
    solution: 'elbow_up' hoặc 'elbow_down'
    Trả về (q1_rad, q2_rad, d1_z) hoặc None nếu tọa độ ngoài tầm với
    """
    # 1. Trục Z hoàn toàn độc lập
    d1_z = z

    # 2. Tính toán động học 2D cho trục X, Y
    d_sq = x * x + y * y
    cos_q2 = (d_sq - l1 * l1 - l2 * l2) / (2.0 * l1 * l2)

    # Kiểm tra giới hạn hình học phẳng
    if cos_q2 < -1.0 or cos_q2 > 1.0:
        return None

    if solution == 'elbow_up':
        sin_q2 = math.sqrt(max(0.0, 1.0 - cos_q2 * cos_q2))
    else:
        sin_q2 = -math.sqrt(max(0.0, 1.0 - cos_q2 * cos_q2))

    q2 = math.atan2(sin_q2, cos_q2)

    k1 = l1 + l2 * math.cos(q2)
    k2 = l2 * math.sin(q2)
    q1 = math.atan2(y, x) - math.atan2(k2, k1)

    return q1, q2, d1_z

def check_reachable(x, y, z, l1, l2, z_min=0.0, z_max=300.0):
    """
    Kiểm tra điểm (x,y,z) có nằm trong vùng không gian làm việc 3D không
    Trả về (bool, message, distance_xy)
    """
    # Kiểm tra hành trình trục Z trước
    if z < z_min or z > z_max:
        return False, f"trục Z ngoài hành trình ({z_min} - {z_max} mm)", 0.0

    # Sau đó mới kiểm tra bán kính với tới trong mặt phẳng XY
    d = math.sqrt(x * x + y * y)
    max_reach = l1 + l2
    min_reach = abs(l1 - l2)

    if d > max_reach:
        return False, f"ngoài tầm với tối đa XY ({max_reach:.1f} mm)", d
    if d < min_reach:
        return False, f"trong vùng chết XY (min {min_reach:.1f} mm)", d
        
    return True, "trong không gian làm việc an toàn", d

def get_workspace_limits(l1, l2):
    """Trả về (max_reach, min_reach) của mặt phẳng XY"""
    return l1 + l2, abs(l1 - l2)
# ============================================================================
# CÁC HÀM TIỆN ÍCH (BỔ SUNG LẠI)
# ============================================================================

def get_joint_positions(q1_rad, q2_rad, l1, l2):
    """
    Lấy tọa độ tất cả các khớp trong mặt phẳng XY
    Trả về (x0,y0, x1,y1, x2,y2)
    """
    x0, y0 = 0.0, 0.0
    x1 = l1 * math.cos(q1_rad)
    y1 = l1 * math.sin(q1_rad)
    x2 = x1 + l2 * math.cos(q1_rad + q2_rad)
    y2 = y1 + l2 * math.sin(q1_rad + q2_rad)
    return x0, y0, x1, y1, x2, y2


def get_circle_points(r, n=200):
    """Tạo điểm vòng tròn bán kính r"""
    angles = np.linspace(0, 2 * math.pi, n)
    x = r * np.cos(angles)
    y = r * np.sin(angles)
    return x, y


def get_jacobian(q1_rad, q2_rad, l1, l2):
    """
    Tính ma trận Jacobian của robot 2R (Mặt phẳng XY)
    """
    j11 = -l1 * math.sin(q1_rad) - l2 * math.sin(q1_rad + q2_rad)
    j12 = -l2 * math.sin(q1_rad + q2_rad)
    j21 =  l1 * math.cos(q1_rad) + l2 * math.cos(q1_rad + q2_rad)
    j22 =  l2 * math.cos(q1_rad + q2_rad)
    return np.array([[j11, j12], [j21, j22]])


def get_manipulability(q1_rad, q2_rad, l1, l2):
    """Tính chỉ số khả năng điều khiển (manipulability)"""
    J = get_jacobian(q1_rad, q2_rad, l1, l2)
    return math.sqrt(max(0.0, np.linalg.det(J @ J.T)))