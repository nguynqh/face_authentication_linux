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

# Kiểm tra các thiết bị camera và đặt quyền truy cập đúng
CAMERA_DEVICES=""
for i in {0..3}; do
    if [ -e "/dev/video$i" ]; then
        CAMERA_DEVICES="$CAMERA_DEVICES /dev/video$i"
        
        # Đặt quyền đọc/ghi cho tất cả người dùng
        log_message "Setting permissions for /dev/video$i"
        chmod a+rw "/dev/video$i" 2>/dev/null || log_message "Failed to chmod /dev/video$i"
        
        # Nếu có nhóm video, thêm vào nhóm video
        if getent group video > /dev/null; then
            chgrp video "/dev/video$i" 2>/dev/null || log_message "Failed to chgrp /dev/video$i"
            chmod g+rw "/dev/video$i" 2>/dev/null || log_message "Failed to set group permissions for /dev/video$i"
            log_message "Set group 'video' for /dev/video$i"
        fi

        # Kiểm tra quyền sau khi đặt
        PERMS=$(stat -c "%a %G %U" "/dev/video$i" 2>/dev/null)
        log_message "Permissions after setting for /dev/video$i: $PERMS"
        
        # Kiểm tra quyền truy cập thực tế
        if [ -r "/dev/video$i" ]; then
            log_message "/dev/video$i is readable"
        else
            log_message "WARNING: /dev/video$i is NOT readable!"
        fi
        
        if [ -w "/dev/video$i" ]; then
            log_message "/dev/video$i is writable"
        else
            log_message "WARNING: /dev/video$i is NOT writable!"
        fi
    fi
done

if [ -z "$CAMERA_DEVICES" ]; then
    log_message "WARNING: No camera devices found!"
else
    log_message "Found camera devices: $CAMERA_DEVICES"
fi

# Đảm bảo thư mục /tmp có quyền ghi cho debug logs
chmod 1777 /tmp 2>/dev/null

# Xác định nếu chạy trong môi trường PAM
export PAM_SERVICE="${PAM_SERVICE:-pam_test}"
log_message "PAM service: $PAM_SERVICE"

# Kiểm tra và thiết lập biến môi trường cho X11
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
    log_message "No DISPLAY set, defaulting to :0"
fi
log_message "Using DISPLAY=$DISPLAY"

# Thiết lập XAUTHORITY cho phiên làm việc hiện tại
if [ "$PAM_SERVICE" = "gdm-password" ] || [ "$PAM_SERVICE" = "lightdm" ] || [ "$PAM_TTY" = ":0" ]; then
    # Đang ở màn hình đăng nhập
    log_message "Login screen detected ($PAM_SERVICE)"
    
    # Tìm file Xauthority thích hợp
    FOUND_AUTH=0
    
    # Thử file của GDM/LightDM trước
    for auth_path in "/run/gdm/auth-for-$CURR_USER-*" "/var/run/gdm/auth-for-$CURR_USER-*" "/var/run/lightdm/root/:0" "/run/lightdm/root/:0"; do
        for file in $auth_path; do
            if [ -f "$file" ]; then
                export XAUTHORITY="$file"
                log_message "Found display manager Xauthority: $XAUTHORITY"
                FOUND_AUTH=1
                break 2
            fi
        done
    done
    
    # Nếu không tìm thấy, thử tạo một cái mới
    if [ $FOUND_AUTH -eq 0 ]; then
        TMP_XAUTH=$(mktemp)
        export XAUTHORITY="$TMP_XAUTH"
        log_message "Created temporary Xauthority at $XAUTHORITY"
        
        # Thử tạo cookie xác thực
        if command -v xauth >/dev/null 2>&1 && command -v mcookie >/dev/null 2>&1; then
            if xauth -f "$XAUTHORITY" add :0 MIT-MAGIC-COOKIE-1 $(mcookie) 2>/dev/null; then
                log_message "Added authentication cookie to Xauthority"
            else
                log_message "Failed to add authentication cookie"
            fi
        else
            log_message "xauth or mcookie command not available"
        fi
    fi
else
    # Đang trong phiên làm việc của người dùng (sudo, screen unlock, etc.)
    log_message "User session detected"
    
    # Sử dụng Xauthority của người dùng nếu tồn tại
    USER_XAUTH="/home/$CURR_USER/.Xauthority"
    if [ -f "$USER_XAUTH" ]; then
        export XAUTHORITY="$USER_XAUTH"
        log_message "Using user's Xauthority: $XAUTHORITY" 
    else
        log_message "User Xauthority not found at $USER_XAUTH"
    fi
fi

# Thiết lập biến môi trường cho việc truy cập X server
export XDG_RUNTIME_DIR="/run/user/$(id -u $CURR_USER 2>/dev/null || echo 1000)"
log_message "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"

# Kiểm tra kết nối X server
if command -v xdpyinfo >/dev/null 2>&1; then
    if xdpyinfo >/dev/null 2>&1; then
        log_message "X server connection test: SUCCESS"
        XSERVER_WORKING=1
    else
        log_message "X server connection test: FAILED. Will try anyway."
        XSERVER_WORKING=0
    fi
else
    log_message "xdpyinfo not available, cannot test X server connection"
    XSERVER_WORKING=0
fi

# Kiểm tra vị trí script xác thực
AUTH_SCRIPT="/home/izzy/Documents/face_authentication_linux/scripts/face_auth.py"
if [ ! -f "$AUTH_SCRIPT" ]; then
    log_message "ERROR: Face auth script not found at $AUTH_SCRIPT"
else
    log_message "Face auth script found at: $AUTH_SCRIPT"
fi

# Ghi log các biến môi trường quan trọng
log_message "Environment: DISPLAY=$DISPLAY, XAUTHORITY=$XAUTHORITY, HOME=$HOME"

# Thiết lập biến môi trường thông báo cho script Python rằng đang chạy trong PAM
export PAM_PYTHON_AUTHENTICATE=1

# Nếu X server không hoạt động, thêm cờ để script Python biết
if [ $XSERVER_WORKING -eq 0 ]; then
    export NO_X_SERVER=1
    log_message "Setting NO_X_SERVER=1 for Python script"
fi

# Chạy script xác thực khuôn mặt
log_message "Running face authentication script"

if [ -f "/home/izzy/Documents/face_authentication_linux/start_face_auth.sh" ]; then
    # Sử dụng script wrapper
    log_message "Using start_face_auth.sh wrapper"
    SCRIPT_OUTPUT=$(/home/izzy/Documents/face_authentication_linux/start_face_auth.sh --username "$CURR_USER" --headless 2>&1)
else
    # Phương án dự phòng
    log_message "start_face_auth.sh not found, using direct Python call"
    
    # Kích hoạt môi trường ảo nếu có
    if [ -f "/home/izzy/Documents/face_authentication_linux/venv/bin/activate" ]; then
        source "/home/izzy/Documents/face_authentication_linux/venv/bin/activate" 2>/dev/null
        log_message "Virtual environment activated"
    fi
    
    cd "/home/izzy/Documents/face_authentication_linux" || log_message "Failed to change directory"
    SCRIPT_OUTPUT=$(python scripts/face_auth.py --username "$CURR_USER" --headless 2>&1)
fi

# Lưu kết quả
EXIT_CODE=$?
log_message "Script output: $SCRIPT_OUTPUT"
log_message "Script exit code: $EXIT_CODE"

# Dọn dẹp file tạm nếu đã tạo
if [ -n "$TMP_XAUTH" ] && [ -f "$TMP_XAUTH" ]; then
    rm -f "$TMP_XAUTH" 2>/dev/null
    log_message "Removed temporary Xauthority file"
fi

# Trả về kết quả
if [ $EXIT_CODE -eq 0 ] && echo "$SCRIPT_OUTPUT" | grep -q "SUCCESS"; then
    log_message "Authentication successful"
    exit 0
else
    log_message "Authentication failed"
    exit 1
fi
