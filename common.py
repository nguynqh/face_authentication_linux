#!/usr/bin/env python3
import os
import cv2
import json
import logging
import numpy as np
import face_recognition
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/var/log/face-auth.log'
)
logger = logging.getLogger('face-auth')

# Các thông số
EAR_THRESHOLD = 0.25
REQUIRED_BLINKS = 2
SHARPNESS_THRESHOLD = 50
FACE_MATCH_THRESHOLD = 0.5

# Thư mục lưu trữ dữ liệu
DATA_DIR = Path.home() / '.face-auth'

def ensure_data_dir():
    """Đảm bảo thư mục dữ liệu tồn tại"""
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created data directory: {DATA_DIR}")
    return DATA_DIR

def calculate_ear(eye):
    """Tính tỷ lệ khía cạnh mắt (EAR)"""
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    return (A + B) / (2.0 * C)

def save_face_encoding(username, face_encoding):
    """Lưu face encoding của người dùng"""
    try:
        ensure_data_dir()
        encoding_file = DATA_DIR / f"{username}.json"
        
        data = {
            "username": username,
            "encoding": face_encoding.tolist() if isinstance(face_encoding, np.ndarray) else face_encoding
        }
        
        with open(encoding_file, 'w') as f:
            json.dump(data, f)
        
        logger.info(f"Saved face encoding for user: {username}")
        return True
    except Exception as e:
        logger.error(f"Error saving face encoding: {str(e)}")
        return False

def load_face_encoding(username):
    """Tải face encoding của người dùng"""
    try:
        encoding_file = DATA_DIR / f"{username}.json"
        
        if not encoding_file.exists():
            logger.warning(f"No face data found for user: {username}")
            return None
                
        with open(encoding_file, 'r') as f:
            data = json.load(f)
        
        return np.array(data["encoding"])
    except Exception as e:
        logger.error(f"Error loading face encoding: {str(e)}")
        return None

def is_face_registered(username):
    """Kiểm tra xem người dùng đã đăng ký khuôn mặt chưa"""
    encoding_file = DATA_DIR / f"{username}.json"
    return encoding_file.exists()

def get_registered_users():
    """Lấy danh sách người dùng đã đăng ký"""
    ensure_data_dir()
    users = []
    for file in DATA_DIR.glob("*.json"):
        users.append(file.stem)
    return users

def run_command(command):
    """Chạy lệnh shell và trả về kết quả"""
    import subprocess
    try:
        return subprocess.check_output(command, shell=True).decode('utf-8').strip()
    except:
        return None
