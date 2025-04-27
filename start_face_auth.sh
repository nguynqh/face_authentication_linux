#!/bin/bash
# Script wrapper để chạy face_auth.py trong môi trường thích hợp

# Xác định đường dẫn tuyệt đối
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || { echo "Không thể thay đổi thư mục đến $SCRIPT_DIR"; exit 1; }

# Tạo file log tạm thời cho debug nếu cần
DEBUG_LOG="/tmp/face_auth_wrapper.log"
echo "===== $(date) =====" >> "$DEBUG_LOG"
echo "Starting wrapper script" >> "$DEBUG_LOG"
echo "Args: $@" >> "$DEBUG_LOG"
echo "Current directory: $(pwd)" >> "$DEBUG_LOG"
echo "User: $(id)" >> "$DEBUG_LOG"

# Đảm bảo quyền truy cập camera trước khi chạy
# Thử với nhiều phương pháp khác nhau để đảm bảo quyền truy cập
echo "Checking camera devices..." >> "$DEBUG_LOG"
CAMERA_FOUND=0

# Liệt kê các thiết bị camera
CAMERA_DEVICES=$(ls -la /dev/video* 2>/dev/null)
echo "Camera devices: $CAMERA_DEVICES" >> "$DEBUG_LOG"

for i in {0..3}; do
    if [ -e "/dev/video$i" ]; then
        CAMERA_FOUND=1
        echo "Setting permissions for /dev/video$i" >> "$DEBUG_LOG"
        
        # Lưu quyền hiện tại
        CURRENT_PERMS=$(stat -c "%a %G %U" "/dev/video$i" 2>/dev/null)
        echo "Current permissions for /dev/video$i: $CURRENT_PERMS" >> "$DEBUG_LOG"
        
        # Thử với quyền root nếu có
        if [ "$(id -u)" -eq 0 ]; then
            chmod 666 "/dev/video$i" 2>/dev/null
            chgrp video "/dev/video$i" 2>/dev/null
            chmod g+rw "/dev/video$i" 2>/dev/null
        fi
        
        # Thử với sudo nếu không phải root
        if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
            sudo chmod 666 "/dev/video$i" 2>/dev/null
            sudo chgrp video "/dev/video$i" 2>/dev/null
            sudo chmod g+rw "/dev/video$i" 2>/dev/null
        fi
        
        # Kiểm tra quyền sau khi thay đổi
        NEW_PERMS=$(stat -c "%a %G %U" "/dev/video$i" 2>/dev/null)
        echo "New permissions for /dev/video$i: $NEW_PERMS" >> "$DEBUG_LOG"
        
        # Kiểm tra quyền truy cập thực tế
        if [ -r "/dev/video$i" ] && [ -w "/dev/video$i" ]; then
            echo "/dev/video$i is readable and writable" >> "$DEBUG_LOG"
        else
            echo "WARNING: /dev/video$i may not have proper access permissions" >> "$DEBUG_LOG"
        fi
    fi
done

# Kiểm tra xem user hiện tại có thuộc group video không
if id -nG | grep -qw "video"; then
    echo "Current user is in video group" >> "$DEBUG_LOG"
else
    echo "WARNING: Current user is NOT in video group" >> "$DEBUG_LOG"
    # Nếu đang chạy với quyền root, có thể thêm người dùng vào nhóm video
    if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
        echo "Adding $SUDO_USER to video group" >> "$DEBUG_LOG"
        usermod -a -G video "$SUDO_USER" 2>/dev/null
    elif [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
        echo "Attempting to add current user to video group via sudo" >> "$DEBUG_LOG"
        sudo usermod -a -G video "$(whoami)" 2>/dev/null
    fi
fi

# Khởi động lại dịch vụ udev nếu không camera nào được tìm thấy
if [ $CAMERA_FOUND -eq 0 ]; then
    echo "No camera devices found, attempting to restart udev" >> "$DEBUG_LOG"
    if [ "$(id -u)" -eq 0 ]; then
        systemctl restart udev 2>/dev/null
        sleep 1
    elif command -v sudo >/dev/null 2>&1; then
        sudo systemctl restart udev 2>/dev/null
        sleep 1
    fi
    
    # Kiểm tra lại sau khi khởi động lại udev
    if ls -la /dev/video* 2>/dev/null; then
        echo "Camera devices found after udev restart" >> "$DEBUG_LOG"
    else
        echo "Still no camera devices after udev restart" >> "$DEBUG_LOG"
    fi
fi

# Kiểm tra nếu cần tải lại driver camera
if ! ls -la /dev/video* 2>/dev/null || ! cat /dev/video0 >/dev/null 2>&1; then
    echo "Testing camera driver" >> "$DEBUG_LOG"
    if lsmod | grep -q uvcvideo; then
        echo "uvcvideo driver is loaded, attempting to reload" >> "$DEBUG_LOG"
        if [ "$(id -u)" -eq 0 ]; then
            modprobe -r uvcvideo 2>/dev/null
            sleep 1
            modprobe uvcvideo 2>/dev/null
        elif command -v sudo >/dev/null 2>&1; then
            sudo modprobe -r uvcvideo 2>/dev/null
            sleep 1
            sudo modprobe uvcvideo 2>/dev/null
        fi
    else
        echo "uvcvideo driver not loaded, attempting to load" >> "$DEBUG_LOG"
        if [ "$(id -u)" -eq 0 ]; then
            modprobe uvcvideo 2>/dev/null
        elif command -v sudo >/dev/null 2>&1; then
            sudo modprobe uvcvideo 2>/dev/null
        fi
    fi
fi

# Kiểm tra xem môi trường ảo có tồn tại không
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    echo "Activating virtual environment" >> "$DEBUG_LOG"
    # shellcheck disable=SC1090
    source "$SCRIPT_DIR/venv/bin/activate" || {
        echo "Không thể kích hoạt môi trường ảo" >> "$DEBUG_LOG"
        echo "Falling back to system Python" >> "$DEBUG_LOG"
    }
else
    echo "Virtual environment not found at $SCRIPT_DIR/venv/bin/activate" >> "$DEBUG_LOG"
    # Kiểm tra xem các package cần thiết có được cài đặt không
    if ! python -c "import cv2, face_recognition, numpy" 2>/dev/null; then
        echo "ERROR: Required Python packages not installed" >> "$DEBUG_LOG"
        echo "FAILURE: Thiếu các thư viện Python cần thiết"
        exit 1
    fi
fi

# Kiểm tra xem Python script có tồn tại không
if [ ! -f "$SCRIPT_DIR/scripts/face_auth.py" ]; then
    echo "ERROR: Face authentication script not found at $SCRIPT_DIR/scripts/face_auth.py" >> "$DEBUG_LOG"
    echo "FAILURE: Script không tồn tại"
    exit 1
fi

# Kiểm tra xem thư mục models có tồn tại và chứa model
if [ ! -f "$SCRIPT_DIR/models/face_auth_model.pkl" ]; then
    echo "ERROR: Face authentication model not found" >> "$DEBUG_LOG"
    echo "FAILURE: Model không tồn tại"
    exit 1
fi

echo "Running face authentication script" >> "$DEBUG_LOG"

# Thiết lập biến môi trường để script Python biết đang chạy trong wrapper
export FACE_AUTH_WRAPPER=1

# Kiểm tra tham số headless
HEADLESS_ARG=""
for arg in "$@"; do
    if [ "$arg" = "--headless" ]; then
        HEADLESS_ARG="--headless"
        echo "Running in headless mode" >> "$DEBUG_LOG"
        break
    fi
done

# Thêm tham số headless nếu cần
if [ -n "$HEADLESS_ARG" ] || [ -n "$NO_X_SERVER" ] || [ -z "$DISPLAY" ]; then
    echo "Adding --headless parameter" >> "$DEBUG_LOG"
    exec python "$SCRIPT_DIR/scripts/face_auth.py" "$@" --headless
else
    # Chạy script xác thực khuôn mặt
    exec python "$SCRIPT_DIR/scripts/face_auth.py" "$@"
fi
