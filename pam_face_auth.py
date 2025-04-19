#!/usr/bin/env python3
import sys
import pwd
import os
import subprocess
import time
from pathlib import Path
import logging
import tempfile

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/var/log/pam-face-auth.log'
)
logger = logging.getLogger('pam-face-auth')

def run_face_auth_gui(username):
    """Chạy giao diện GTK cho xác thực khuôn mặt và trả về kết quả"""
    # Lấy thông tin người dùng
    try:
        pw_record = pwd.getpwnam(username)
        user_home = pw_record.pw_dir
        user_uid = pw_record.pw_uid
        user_gid = pw_record.pw_gid
    except KeyError:
        logger.error(f"User {username} does not exist")
        return False
    
    # Tạo file tạm để lưu kết quả
    result_file = tempfile.NamedTemporaryFile(delete=False)
    result_path = result_file.name
    result_file.close()
    
    # Tạo file lock để kiểm soát quá trình
    lock_file = tempfile.NamedTemporaryFile(delete=False)
    lock_path = lock_file.name
    lock_file.close()
    
    # Lấy biến môi trường DISPLAY và XAUTHORITY
    display = os.environ.get('DISPLAY', ':0')
    xauthority = os.environ.get('XAUTHORITY', os.path.join(user_home, '.Xauthority'))
    
    # Tạo lệnh chạy giao diện xác thực
    cmd = [
        "sudo", "-u", username,
        "env", f"DISPLAY={display}", f"XAUTHORITY={xauthority}",
        "python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_auth_gui.py"),
        username, result_path, lock_path
    ]
    
    try:
        # Chạy giao diện xác thực
        process = subprocess.Popen(cmd)
        
        # Chờ cho tới khi xác thực hoàn thành hoặc timeout
        timeout = 30  # Tối đa 30 giây
        start_time = time.time()
        
        while os.path.exists(lock_path) and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        # Đọc kết quả
        if os.path.exists(result_path):
            with open(result_path, 'r') as f:
                result = f.read().strip()
            
            # Xóa các file tạm
            try:
                os.unlink(result_path)
                if os.path.exists(lock_path):
                    os.unlink(lock_path)
            except:
                pass
            
            return result == "SUCCESS"
        
        return False
        
    except Exception as e:
        logger.error(f"Error running face auth GUI: {str(e)}")
        return False

def pam_sm_authenticate(pamh, flags, argv):
    """
    PAM service function for authentication
    """
    # Lấy tên người dùng
    try:
        username = pamh.get_user()
    except pamh.exception as e:
        return pamh.PAM_AUTH_ERR
    
    if not username:
        return pamh.PAM_USER_UNKNOWN
    
    # Kiểm tra xem người dùng có đăng ký khuôn mặt chưa
    face_auth_dir = Path.home() / '.face-auth'
    face_data_file = face_auth_dir / f"{username}.json"
    
    if not face_data_file.exists():
        # Người dùng chưa đăng ký khuôn mặt, sử dụng phương thức xác thực khác
        return pamh.PAM_AUTHINFO_UNAVAIL
    
    # Hiển thị giao diện xác thực khuôn mặt
    auth_success = run_face_auth_gui(username)
    
    if auth_success:
        return pamh.PAM_SUCCESS
    else:
        return pamh.PAM_AUTH_ERR

def pam_sm_setcred(pamh, flags, argv):
    """
    PAM service function for setting credentials
    """
    return pamh.PAM_SUCCESS

def pam_sm_acct_mgmt(pamh, flags, argv):
    """
    PAM service function for account management
    """
    return pamh.PAM_SUCCESS

def pam_sm_open_session(pamh, flags, argv):
    """
    PAM service function for opening a session
    """
    return pamh.PAM_SUCCESS

def pam_sm_close_session(pamh, flags, argv):
    """
    PAM service function for closing a session
    """
    return pamh.PAM_SUCCESS

def pam_sm_chauthtok(pamh, flags, argv):
    """
    PAM service function for changing authentication token
    """
    return pamh.PAM_SUCCESS
