#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil

def check_root():
    if os.geteuid() != 0:
        print("Script này cần chạy với quyền root!")
        sys.exit(1)

def install_dependencies():
    print("Đang cài đặt các gói phụ thuộc...")
    
    # Cài đặt các gói hệ thống
    subprocess.run(['apt-get', 'update'])
    subprocess.run(['apt-get', 'install', '-y', 
                   'python3-pip',
                   'python3-opencv',
                   'python3-pyqt5',
                   'cmake',
                   'build-essential',
                   'libopenblas-dev',
                   'liblapack-dev',
                   'libx11-dev',
                   'libgtk-3-dev',
                   'pkg-config'])
    
    # Cài đặt dlib riêng trước
    print("Đang cài đặt dlib...")
    subprocess.run(['pip3', 'install', 'dlib'])
    
    # Cài đặt các thư viện Python còn lại
    print("Đang cài đặt các thư viện Python...")
    subprocess.run(['pip3', 'install', '-r', 'requirements.txt'])

def setup_autostart():
    print("Đang cấu hình tự động khởi động...")
    
    # Tạo service file
    service_content = """[Unit]
Description=Face Authentication Login
After=graphical.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {}/scripts/ubuntu_login_integration.py
Restart=always
User=root

[Install]
WantedBy=graphical.target
""".format(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
    
    # Lưu service file
    with open('/etc/systemd/system/face-auth-login.service', 'w') as f:
        f.write(service_content)
    
    # Reload systemd và kích hoạt service
    subprocess.run(['systemctl', 'daemon-reload'])
    subprocess.run(['systemctl', 'enable', 'face-auth-login.service'])

def setup_permissions():
    print("Đang cấu hình quyền truy cập...")
    
    # Tạo thư mục data nếu chưa tồn tại
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Cấp quyền cho các script
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts')
    for script in os.listdir(scripts_dir):
        if script.endswith('.py'):
            script_path = os.path.join(scripts_dir, script)
            os.chmod(script_path, 0o755)
    
    # Cấp quyền cho thư mục data
    os.chmod(data_dir, 0o777)

def verify_installation():
    print("Đang kiểm tra cài đặt...")
    try:
        import PyQt5.QtWidgets
        import cv2
        import face_recognition
        import dlib
        print("✓ Tất cả các thư viện đã được cài đặt thành công!")
    except ImportError as e:
        print(f"✗ Lỗi: {str(e)}")
        print("Vui lòng chạy lại script cài đặt.")
        sys.exit(1)

def main():
    check_root()
    
    print("Bắt đầu cài đặt hệ thống xác thực khuôn mặt...")
    
    # Cài đặt các gói phụ thuộc
    install_dependencies()
    
    # Kiểm tra cài đặt
    verify_installation()
    
    # Cấu hình tự động khởi động
    setup_autostart()
    
    # Cấu hình quyền truy cập
    setup_permissions()
    
    print("\nCài đặt hoàn tất!")
    print("Hệ thống sẽ được kích hoạt sau khi khởi động lại.")
    print("Bạn có thể chạy lệnh sau để khởi động lại:")
    print("sudo reboot")

if __name__ == '__main__':
    main() 