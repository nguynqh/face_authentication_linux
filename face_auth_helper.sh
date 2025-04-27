#!/bin/bash

# Tạo file log (nếu chưa có) và đặt quyền
LOG_FILE="/tmp/face_auth.log"
if [ ! -f "$LOG_FILE" ]; then
    touch "$LOG_FILE" 2>/dev/null
    chmod 666 "$LOG_FILE" 2>/dev/null
fi

# Hàm ghi log an toàn (không gây lỗi nếu không ghi được)
log_message() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" >> "$LOG_FILE" 2>/dev/null
}

# Ghi log khởi động
log_message "Starting face authentication"

# Lấy thông tin người dùng hiện tại
CURR_USER="${PAM_USER:-izzy}"
log_message "Authenticating for user: $CURR_USER"

# Xác định ID người dùng
USER_ID=$(id -u $CURR_USER 2>/dev/null)
if [ -z "$USER_ID" ]; then
    log_message "Cannot determine user ID, defaulting to 1000"
    USER_ID=1000
else
    log_message "User ID: $USER_ID"
fi

# Phát hiện môi trường hiện tại (GDM login vs session)
if [ -z "$DISPLAY" ]; then
    # Nếu không có DISPLAY, giả định đây là màn hình đăng nhập GDM
    export DISPLAY=:0
    log_message "No DISPLAY set, defaulting to :0"
fi
log_message "Using DISPLAY=$DISPLAY"

# Đặt các biến môi trường X11 hiển thị
if [ "$PAM_SERVICE" = "gdm-password" ] || [ "$PAM_TTY" = ":0" ]; then
    # Đang ở màn hình đăng nhập GDM
    log_message "GDM login screen detected"
    
    # Cho phép tất cả người dùng local truy cập vào X server tạm thời
    xhost +local: >> "$LOG_FILE" 2>&1
    
    # Sử dụng Xauthority của GDM
    export XAUTHORITY=/var/run/gdm3/auth-for-$CURR_USER-*/database
    # Nếu không tìm thấy Xauthority cụ thể, thử các vị trí phổ biến
    if [ ! -f "$XAUTHORITY" ]; then
        for auth_file in /run/gdm/*/database /var/run/gdm*/*/database /var/lib/gdm*/*/database; do
            if [ -f "$auth_file" ]; then
                export XAUTHORITY="$auth_file"
                log_message "Found Xauthority at $XAUTHORITY"
                break
            fi
        done
    fi
else
    # Đang trong phiên đăng nhập (sudo, lock screen, etc)
    log_message "User session detected"
    export XAUTHORITY=/home/$CURR_USER/.Xauthority
fi

export HOME=/home/$CURR_USER
log_message "Using XAUTHORITY=$XAUTHORITY"

# Kiểm tra xem có thể truy cập X server không
if ! xdpyinfo >/dev/null 2>&1; then
    log_message "ERROR: Cannot access X server with current settings!"
else
    log_message "Successfully connected to X server"
fi

# Gọi script xác thực khuôn mặt
log_message "Running face authentication script"
SCRIPT_OUTPUT=$(/home/izzy/Documents/face_authentication_linux/start_face_auth.sh --username "$CURR_USER" 2>&1)

# Lưu mã thoát và output
EXIT_CODE=$?
log_message "Authentication script output: $SCRIPT_OUTPUT"
log_message "Authentication script exit code: $EXIT_CODE"

# Dọn dẹp (nếu đã cho phép truy cập X server)
if [ "$PAM_SERVICE" = "gdm-password" ] || [ "$PAM_TTY" = ":0" ]; then
    xhost -local: >> "$LOG_FILE" 2>&1 || true
fi

# Trả về kết quả cho PAM
if [ $EXIT_CODE -eq 0 ] && echo "$SCRIPT_OUTPUT" | grep -q "SUCCESS"; then
    log_message "Authentication successful"
    exit 0
else
    log_message "Authentication failed"
    exit 1
fi
