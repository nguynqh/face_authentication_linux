#!/usr/bin/env python3

import os
import sys
import time
import logging
import subprocess
import signal
import shutil
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/var/log/face-auth.log'
)
logger = logging.getLogger('face-auth-service')

def create_directories():
    """Tạo các thư mục cần thiết"""
    directories = [
        '/var/lib/face-auth',
        '/var/lib/face-auth/images',
        '/usr/share/face-auth'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        if directory.startswith('/var/lib/face-auth'):
            # Đặt quyền cho thư mục data
            os.chmod(directory, 0o755)

def check_dependencies():
    """Kiểm tra các phụ thuộc cần thiết"""
    try:
        import cv2
        import dlib
        import face_recognition
        import numpy
        logger.info("All required Python dependencies are installed")
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {str(e)}")
        return False

def check_model_files():
    """Kiểm tra các file model cần thiết"""
    model_path = '/usr/share/face-auth/shape_predictor_68_face_landmarks.dat'
    if not os.path.exists(model_path):
        logger.warning(f"Missing model file: {model_path}")
        
        # Thử tìm model trong các đường dẫn khác nhau
        possible_paths = [
            '/usr/local/share/dlib/shape_predictor_68_face_landmarks.dat',
            '/usr/share/dlib/shape_predictor_68_face_landmarks.dat',
            '/var/lib/face-auth/shape_predictor_68_face_landmarks.dat'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found model file at {path}, copying to {model_path}")
                shutil.copy(path, model_path)
                return True
        
        logger.error("Could not find shape_predictor_68_face_landmarks.dat model file")
        return False
    
    return True

def check_camera():
    """Kiểm tra xem camera có hoạt động không"""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Camera không thể mở")
            return False
        
        ret, frame = cap.read()
        if not ret or frame is None:
            logger.error("Không thể đọc từ camera")
            cap.release()
            return False
        
        logger.info("Camera hoạt động bình thường")
        cap.release()
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra camera: {str(e)}")
        return False

def check_authentication_system():
    """Kiểm tra hệ thống xác thực khuôn mặt"""
    pam_module_path = '/lib/security/pam_face_auth.so'
    if not os.path.exists(pam_module_path):
        logger.error(f"PAM module không tồn tại: {pam_module_path}")
        return False
    
    # Kiểm tra xem PAM đã được cấu hình chính xác chưa
    pam_configs = [
        '/etc/pam.d/gdm-password',
        '/etc/pam.d/lightdm',
        '/etc/pam.d/login',
    ]
    
    configured = False
    for config in pam_configs:
        if os.path.exists(config):
            with open(config, 'r') as f:
                if 'pam_face_auth.so' in f.read():
                    configured = True
                    logger.info(f"PAM đã được cấu hình trong {config}")
                    break
    
    if not configured:
        logger.warning("PAM module chưa được cấu hình trong bất kỳ file nào")
        return False
    
    return True

def monitor_system():
    """Kiểm tra định kỳ hệ thống"""
    camera_ok = check_camera()
    auth_system_ok = check_authentication_system()
    
    if not camera_ok:
        logger.error("Hệ thống xác thực khuôn mặt có thể không hoạt động - Camera không khả dụng")
    
    if not auth_system_ok:
        logger.error("Hệ thống xác thực khuôn mặt có thể không được cấu hình đúng")
    
    # Đếm số người dùng đã đăng ký
    user_count = 0
    for file in os.listdir('/var/lib/face-auth'):
        if file.endswith('.txt'):
            user_count += 1
    
    logger.info(f"Số người dùng đã đăng ký xác thực khuôn mặt: {user_count}")
    return camera_ok and auth_system_ok

def cleanup():
    """Dọn dẹp trước khi thoát"""
    logger.info("Dịch vụ xác thực khuôn mặt đang dừng")

def signal_handler(sig, frame):
    """Xử lý tín hiệu ngắt"""
    logger.info(f"Nhận tín hiệu {sig}, đang thoát...")
    cleanup()
    sys.exit(0)

def main():
    """Hàm chính của dịch vụ"""
    logger.info("Dịch vụ xác thực khuôn mặt đang khởi động")
    
    # Đăng ký xử lý tín hiệu
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Khởi tạo hệ thống
    create_directories()
    
    # Kiểm tra các phụ thuộc và cài đặt
    dependencies_ok = check_dependencies()
    model_files_ok = check_model_files()
    
    if not dependencies_ok:
        logger.error("Thiếu các phụ thuộc cần thiết, dịch vụ có thể không hoạt động đúng")
    
    if not model_files_ok:
        logger.error("Thiếu các file model cần thiết, dịch vụ có thể không hoạt động đúng")
    
    # Vòng lặp chính
    try:
        while True:
            # Kiểm tra hệ thống
            monitor_system()
            
            # Ngủ 5 phút trước khi kiểm tra lại
            time.sleep(300)
    
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {str(e)}")
        return 1
    
    finally:
        cleanup()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
