#!/bin/bash

# Script cài đặt Face Authentication cho Ubuntu 24.04
set -e

echo "Bắt đầu cài đặt Face Authentication cho Ubuntu 24.04"

# Kiểm tra quyền root
if [ "$(id -u)" != "0" ]; then
   echo "Script này cần chạy với quyền root" 
   exit 1
fi

# Cài đặt các gói phụ thuộc
echo "Cài đặt các gói phụ thuộc..."
apt-get update
apt-get install -y build-essential libpam0g-dev libgtk-3-dev python3-pip \
    python3-dev python3-opencv python3-gi python3-cairo python3-gi-cairo \
    gir1.2-gtk-3.0 v4l-utils cmake

# Cài đặt thư viện Python
echo "Cài đặt các gói Python..."
#pip3 install face-recognition dlib numpy imutils

# Tạo cấu trúc thư mục
echo "Tạo cấu trúc thư mục..."
mkdir -p /usr/lib/face-auth/face_auth
mkdir -p /usr/share/face-auth
mkdir -p /var/lib/face-auth
mkdir -p /usr/bin

# Biên dịch PAM module
echo "Biên dịch PAM module..."
cd pam_module
make
make install
cd ..

# Cài đặt các file Python
echo "Cài đặt các file Python..."
cp face_auth/*.py /usr/lib/face-auth/face_auth/
cp face_auth_ui/*.py /usr/lib/face-auth/

# Tạo file __init__.py để làm module
touch /usr/lib/face-auth/face_auth/__init__.py

# Cài đặt script đăng ký
cp utils/face_auth_register /usr/bin/
chmod +x /usr/bin/face_auth_register

# Tạo symlink cho giao diện người dùng
# QUAN TRỌNG: Di chuyển phần này xuống sau khi đã sao chép file
echo "Tạo symlink cho giao diện người dùng..."
#ln -sf /usr/lib/face-auth/auth_ui.py /usr/bin/face_auth_ui
#ln -sf /usr/lib/face-auth/register_ui.py /usr/bin/face_auth_register_ui
#chmod +x /usr/bin/face_auth_ui
#chmod +x /usr/bin/face_auth_register_ui

# Cài đặt service
cp systemd/face-auth.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable face-auth.service
systemctl start face-auth.service

# Tải model shape predictor nếu chưa có
if [ ! -f "/usr/share/face-auth/shape_predictor_68_face_landmarks.dat" ]; then
    echo "Tải model dlib shape predictor..."
    mkdir -p /tmp/dlib_models
    cd /tmp/dlib_models
    
    # Tải model từ GitHub hoặc mirror
    wget -O shape_predictor_68_face_landmarks.dat.bz2 "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2" || \
    wget -O shape_predictor_68_face_landmarks.dat.bz2 "https://github.com/davisking/dlib-models/raw/master/shape_predictor_68_face_landmarks.dat.bz2"
    
    # Giải nén
    bzip2 -d shape_predictor_68_face_landmarks.dat.bz2
    cp shape_predictor_68_face_landmarks.dat /usr/share/face-auth/
    cd /
    rm -rf /tmp/dlib_models
fi

# Cấu hình PAM
echo "Cấu hình PAM..."
# Tạo backup
cp /etc/pam.d/gdm-password /etc/pam.d/gdm-password.bak

# Thêm module vào cấu hình PAM nếu chưa có
if ! grep -q "pam_face_auth.so" /etc/pam.d/gdm-password; then
    # Thêm sau pam_unix.so với chế độ sufficient để có thể bỏ qua nếu xác thực thất bại
    sed -i '/auth[[:space:]]*sufficient[[:space:]]*pam_unix.so/a auth    sufficient      pam_face_auth.so' /etc/pam.d/gdm-password
fi

echo "Cài đặt hoàn tất!"
echo "Hãy đăng ký khuôn mặt của bạn bằng cách chạy: face_auth_register"
