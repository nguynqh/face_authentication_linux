#!/bin/bash

# Script này cấu hình xác thực khuôn mặt tại màn hình đăng nhập GDM

# Kiểm tra quyền root
if [ "$(id -u)" -ne 0 ]; then
   echo "Phải chạy script này với quyền sudo" 
   echo "Ví dụ: sudo ./setup_login_auth.sh"
   exit 1
fi

# Tạo bản sao lưu nếu chưa có
if [ ! -f "/etc/pam.d/gdm-password.backup" ]; then
    echo "Tạo bản sao lưu của /etc/pam.d/gdm-password"
    cp /etc/pam.d/gdm-password /etc/pam.d/gdm-password.backup
fi

# Kiểm tra xem cấu hình đã được thêm chưa
if grep -q "pam_face_auth.so" /etc/pam.d/gdm-password; then
    echo "Cấu hình xác thực khuôn mặt đã tồn tại trong file GDM password"
else
    echo "Thêm cấu hình xác thực khuôn mặt vào GDM password"
    
    # Tạo file tạm thời
    cat > /tmp/gdm-password.new << EOL
# Xác thực khuôn mặt cho GDM
auth sufficient pam_exec.so expose_authtok /usr/local/bin/face_auth_helper.sh
auth sufficient pam_face_auth.so

# Cấu hình gốc
$(cat /etc/pam.d/gdm-password)
EOL
    
    # Thay thế file cũ
    mv /tmp/gdm-password.new /etc/pam.d/gdm-password
    
    # Đảm bảo quyền đúng
    chmod 644 /etc/pam.d/gdm-password
fi

echo "Hoàn thành cấu hình xác thực khuôn mặt cho màn hình đăng nhập"
echo "Hãy khởi động lại để kiểm tra"