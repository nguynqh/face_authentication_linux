#!/bin/bash

# Tạo file log (nếu chưa có) và đặt quyền
LOG_FILE="/tmp/face_auth.log"
if [ ! -f "$LOG_FILE" ]; then
    touch "$LOG_FILE" 2>/dev/null
    chmod 666 "$LOG_FILE" 2>/dev/null
fi

# Hàm ghi log an toàn (không gây lỗi nếu không ghi được)
log_message() {
    echo "$1" >> "$LOG_FILE" 2>/dev/null
}

# Ghi log khởi động
log_message "Starting face authentication at $(date)"

# Lấy thông tin người dùng hiện tại
CURR_USER="${PAM_USER:-izzy}"
USER_ID=$(id -u $CURR_USER)

log_message "Authenticating for user: $CURR_USER"

# Đặt các biến môi trường X11 hiển thị
export DISPLAY=:0
export XAUTHORITY=/home/$CURR_USER/.Xauthority
export HOME=/home/$CURR_USER

# Gọi script xác thực khuôn mặt
/home/izzy/Documents/face_authentication_linux/start_face_auth.sh --username "$CURR_USER" >> "$LOG_FILE" 2>&1

# Lưu mã thoát
EXIT_CODE=$?
log_message "Face auth exited with code: $EXIT_CODE"

# Trả về kết quả cho PAM
if [ $EXIT_CODE -eq 0 ]; then
    log_message "Authentication successful"
    exit 0
else
    log_message "Authentication failed"
    exit 1
fi
