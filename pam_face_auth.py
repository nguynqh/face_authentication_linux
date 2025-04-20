#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import tempfile
import logging
from pathlib import Path

sys.path.append('/usr/lib/face-auth')
from common import (
    is_face_registered, load_face_encoding, logger, 
    run_command
)

def pam_sm_authenticate(pamh, flags, argv):
    try:
        # Lấy thông tin người dùng
        user = pamh.get_user()
        if not user:
            logger.error("Không thể lấy tên người dùng")
            return pamh.PAM_AUTH_ERR
        
        # Tên người dùng
        username = user
        
        # Kiểm tra xem người dùng đã đăng ký khuôn mặt chưa
        if not is_face_registered(username):
            logger.info(f"Người dùng {username} chưa đăng ký khuôn mặt")
            return pamh.PAM_AUTH_ERR
        
        # Tạo các file tạm thời để lưu kết quả
        with tempfile.NamedTemporaryFile(delete=False) as tmp_result:
            result_path = tmp_result.name
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_lock:
            lock_path = tmp_lock.name
        
        # Gọi GUI xác thực
        cmd = [
            "/usr/lib/face-auth/face-auth-gui",
            username,
            result_path,
            lock_path
        ]
        
        # Lấy session hiện tại
        display = os.environ.get('DISPLAY')
        if not display:
            # Tìm display của người dùng hiện tại
            display = run_command(f"w -h {username} | grep -m 1 ':[0-9]\\+' | sed -E 's/.*\\s+:(\\S+).*/:\\1/'")
            if not display:
                display = ":0"
        
        # Chạy GUI với DISPLAY của người dùng
        env = os.environ.copy()
        env['DISPLAY'] = display
        env['XAUTHORITY'] = run_command(f"find /run/user/$(id -u {username}) -name Xauthority") or ""
        
        proc = subprocess.Popen(cmd, env=env)
        
        # Chờ và kiểm tra kết quả
        while os.path.exists(lock_path):
            time.sleep(0.1)
        
        try:
            with open(result_path, 'r') as f:
                result = f.read().strip()
            
            # Xử lý kết quả
            if result == "SUCCESS":
                logger.info(f"Xác thực thành công cho {username}")
                return pamh.PAM_SUCCESS
            elif result == "CANCEL":
                # Người dùng đã hủy -> chuyển về xác thực mật khẩu
                logger.info(f"Người dùng {username} đã hủy xác thực khuôn mặt")
                return pamh.PAM_AUTH_ERR
            elif result == "MAX_ATTEMPTS_REACHED":
                logger.info(f"Người dùng {username} đã hết số lần thử")
                return pamh.PAM_AUTH_ERR
            else:
                logger.error(f"Kết quả không xác định: {result}")
                return pamh.PAM_AUTH_ERR
                
        except Exception as e:
            logger.error(f"Lỗi đọc file kết quả: {str(e)}")
            return pamh.PAM_AUTH_ERR
        finally:
            # Xóa các file tạm
            try:
                if os.path.exists(result_path):
                    os.unlink(result_path)
                if os.path.exists(lock_path):
                    os.unlink(lock_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Lỗi xác thực: {str(e)}")
        return pamh.PAM_AUTH_ERR

def pam_sm_setcred(pamh, flags, argv):
    return pamh.PAM_SUCCESS

def pam_sm_acct_mgmt(pamh, flags, argv):
    return pamh.PAM_SUCCESS

def pam_sm_open_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS

def pam_sm_close_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS

def pam_sm_chauthtok(pamh, flags, argv):
    return pamh.PAM_SUCCESS
