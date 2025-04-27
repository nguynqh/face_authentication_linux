#!/bin/bash
# Script để tích hợp giao diện xác thực khuôn mặt với màn hình khóa hệ thống

# Đặt đường dẫn
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_SCREEN_AUTH_SCRIPT="$SCRIPT_DIR/scripts/face_auth.py" # Changed from lock_screen_auth.py
CONFIG_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$CONFIG_DIR/face_auth_lockscreen.desktop"

# Cài đặt hook cho các sự kiện màn hình khóa
setup_lock_hooks() {
    echo "Đang cài đặt hook cho màn hình khóa..."
    
    # Phát hiện môi trường Desktop
    if [[ "$XDG_CURRENT_DESKTOP" == *"GNOME"* ]]; then
        setup_gnome_hooks
    elif [[ "$XDG_CURRENT_DESKTOP" == *"KDE"* ]]; then
        setup_kde_hooks
    elif [[ "$XDG_CURRENT_DESKTOP" == *"XFCE"* ]]; then
        setup_xfce_hooks
    else
        echo "Môi trường desktop không được hỗ trợ đầy đủ, sẽ sử dụng phương pháp tổng quát."
        setup_generic_hooks
    fi
}

# Thiết lập hook cho GNOME
setup_gnome_hooks() {
    echo "Đang thiết lập hook cho GNOME..."
    
    # Tạo thư mục dbus service nếu chưa tồn tại
    mkdir -p "$HOME/.local/share/dbus-1/services"
    
    # Tạo file dịch vụ gắn hook
    cat > "$HOME/.local/share/dbus-1/services/org.gnome.ScreenSaver.service" << EOF
[D-BUS Service]
Name=org.gnome.ScreenSaver
Exec=/bin/bash $SCRIPT_DIR/lockscreen_integration.sh --monitor-lock
EOF
    
    echo "Đã thiết lập dịch vụ hook cho GNOME"
    
    # Kích hoạt giám sát màn hình khóa thông qua gsettings
    gsettings set org.gnome.desktop.screensaver lock-enabled true
}

# Thiết lập hook cho KDE
setup_kde_hooks() {
    echo "Đang thiết lập hook cho KDE..."
    
    # Tạo script autostart
    mkdir -p "$HOME/.config/plasma-workspace/shutdown"
    
    # Tạo script theo dõi màn hình khóa
    cat > "$HOME/.config/plasma-workspace/shutdown/face_auth_lock.sh" << EOF
#!/bin/bash
export DISPLAY=:0
/bin/bash $SCRIPT_DIR/lockscreen_integration.sh --monitor-lock
EOF
    
    chmod +x "$HOME/.config/plasma-workspace/shutdown/face_auth_lock.sh"
    
    echo "Đã thiết lập hook cho KDE Plasma"
}

# Thiết lập hook cho XFCE
setup_xfce_hooks() {
    echo "Đang thiết lập hook cho XFCE..."
    
    # Tạo hook cho xfce4-screensaver
    mkdir -p "$HOME/.config/xfce4/xfconf/xfce-perchannel-xml"
    
    # Tạo script helper
    cat > "$HOME/.local/bin/xfce-face-auth-helper.sh" << EOF
#!/bin/bash
export DISPLAY=:0
/bin/bash $SCRIPT_DIR/lockscreen_integration.sh --monitor-lock
EOF
    
    chmod +x "$HOME/.local/bin/xfce-face-auth-helper.sh"
    
    # Thêm vào autostart
    xfconf-query -c xfce4-session -p /startup/autostart -t string -s "$HOME/.local/bin/xfce-face-auth-helper.sh" --create
    
    echo "Đã thiết lập hook cho XFCE"
}

# Thiết lập hook tổng quát
setup_generic_hooks() {
    echo "Đang thiết lập hook tổng quát cho các môi trường desktop khác..."
    
    # Tạo thư mục scripts nếu chưa tồn tại
    mkdir -p "$HOME/.local/bin"
    
    # Tạo script helper
    cat > "$HOME/.local/bin/face-auth-lockscreen-helper.sh" << EOF
#!/bin/bash
# Script theo dõi trạng thái màn hình khóa

export DISPLAY=:0
LOCKFILE="/tmp/screen_locked_state"

# Hàm theo dõi trạng thái màn hình khóa
monitor_lock_state() {
    # Xóa file trạng thái
    rm -f "\$LOCKFILE"
    
    while true; do
        # Kiểm tra trạng thái màn hình với nhiều phương pháp khác nhau
        LOCKED=false
        
        # Kiểm tra với loginctl
        if loginctl show-session | grep -q "LockedHint=yes"; then
            LOCKED=true
        fi
        
        # Kiểm tra với dbus cho GNOME
        if dbus-send --session --dest=org.gnome.ScreenSaver --type=method_call --print-reply --reply-timeout=1000 \
            /org/gnome/ScreenSaver org.gnome.ScreenSaver.GetActive 2>/dev/null | grep -q "boolean true"; then
            LOCKED=true
        fi
        
        # Kiểm tra với các hệ thống khác
        if pidof gnome-screensaver xfce4-screensaver light-locker mate-screensaver >/dev/null; then
            LOCKED=true
        fi
        
        # Nếu đang khóa và chưa hiển thị giao diện xác thực
        if [ "\$LOCKED" = "true" ] && [ ! -f "\$LOCKFILE" ]; then
            touch "\$LOCKFILE"
            $SCRIPT_DIR/lockscreen_integration.sh --launch &
        fi
        
        # Nếu không còn khóa, xóa file trạng thái
        if [ "\$LOCKED" = "false" ] && [ -f "\$LOCKFILE" ]; then
            rm -f "\$LOCKFILE"
        fi
        
        sleep 1
    done
}

monitor_lock_state &
EOF
    
    chmod +x "$HOME/.local/bin/face-auth-lockscreen-helper.sh"
    
    # Thêm vào autostart
    if [ ! -f "$CONFIG_DIR/face_auth_generic.desktop" ]; then
        cat > "$CONFIG_DIR/face_auth_generic.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Face Authentication Generic Helper
Comment=Monitor lock screen for face authentication
Exec=$HOME/.local/bin/face-auth-lockscreen-helper.sh
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
EOF
        chmod +x "$CONFIG_DIR/face_auth_generic.desktop"
    fi
    
    echo "Đã thiết lập hook tổng quát"
}

# Hàm khởi chạy giao diện xác thực
launch_auth_interface() {
    # Lấy tên người dùng hiện tại
    CURRENT_USER=$(whoami)
    
    # Kiểm tra xem giao diện đã chạy chưa
    if pgrep -f "python.*face_auth.py --username $CURRENT_USER" >/dev/null; then # Updated pgrep pattern
        echo "Giao diện xác thực đã đang chạy cho người dùng $CURRENT_USER"
        return
    fi
    
    # Chờ 1 giây để màn hình khóa hoàn thành trước
    sleep 1
    
    # Kiểm tra Python và môi trường ảo
    PYTHON_CMD="python3"
    if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
        PYTHON_CMD="$SCRIPT_DIR/venv/bin/python"
    fi
    
    # Khởi chạy giao diện xác thực với tên người dùng
    echo "Khởi chạy giao diện xác thực cho $CURRENT_USER"
    DISPLAY=:0 $PYTHON_CMD "$LOCK_SCREEN_AUTH_SCRIPT" --username "$CURRENT_USER" &
}

# Hàm giám sát trạng thái màn hình khóa
monitor_lock_screen() {
    # Xóa bất kỳ file cũ nào
    rm -f "/tmp/screen_locked_state"
    
    while true; do
        # Kiểm tra trạng thái màn hình với nhiều phương pháp
        LOCKED=false
        
        # Kiểm tra với loginctl
        if loginctl show-session | grep -q "LockedHint=yes"; then
            LOCKED=true
        fi
        
        # Kiểm tra với GNOME
        if [ "$XDG_CURRENT_DESKTOP" == "GNOME" ]; then
            if dbus-send --session --dest=org.gnome.ScreenSaver --type=method_call --print-reply --reply-timeout=1000 \
                /org/gnome/ScreenSaver org.gnome.ScreenSaver.GetActive 2>/dev/null | grep -q "boolean true"; then
                LOCKED=true
            fi
        fi
        
        # Kiểm tra với các hệ thống khác
        if pidof gnome-screensaver xfce4-screensaver light-locker mate-screensaver >/dev/null; then
            LOCKED=true
        fi
        
        # Nếu đang khóa và chưa hiển thị giao diện xác thực
        if [ "$LOCKED" = "true" ] && [ ! -f "/tmp/screen_locked_state" ]; then
            touch "/tmp/screen_locked_state"
            launch_auth_interface
        fi
        
        # Nếu không còn khóa, xóa file trạng thái
        if [ "$LOCKED" = "false" ] && [ -f "/tmp/screen_locked_state" ]; then
            rm -f "/tmp/screen_locked_state"
        fi
        
        sleep 1
    done
}

# Menu lựa chọn chức năng
show_menu() {
    echo "===== TÍCH HỢP GIAO DIỆN XÁC THỰC KHUÔN MẶT VỚI MÀN HÌNH KHÓA ====="
    echo "1. Thiết lập hook cho màn hình khóa"
    echo "2. Khởi động giao diện xác thực (thủ công)" # Renumbered
    echo "3. Kiểm tra cài đặt" # Renumbered
    echo "4. Thoát" # Renumbered
    
    read -p "Vui lòng chọn một tùy chọn: " choice
    
    case $choice in
        1) setup_lock_hooks ;; # Removed create_desktop_file call
        2) launch_auth_interface ;; # Renumbered
        3) check_installation ;; # Renumbered
        4) exit 0 ;; # Renumbered
        *) echo "Lựa chọn không hợp lệ!" ;;
    esac
}

# Kiểm tra cài đặt
check_installation() {
    echo "===== KIỂM TRA CÀI ĐẶT ====="
    
    # Kiểm tra script xác thực
    echo -n "Kiểm tra script xác thực khuôn mặt: "
    if [ -f "$LOCK_SCREEN_AUTH_SCRIPT" ]; then
        echo "OK"
    else
        echo "KHÔNG TÌM THẤY"
    fi
    
    # Kiểm tra file desktop
    echo -n "Kiểm tra file desktop: "
    if [ -f "$DESKTOP_FILE" ]; then
        echo "OK"
        grep -q "Exec" "$DESKTOP_FILE" && echo "  - Cấu hình Exec: OK" || echo "  - Cấu hình Exec: LỖI"
    else
        echo "KHÔNG TÌM THẤY"
    fi
    
    # Kiểm tra môi trường desktop
    echo "Môi trường desktop hiện tại: $XDG_CURRENT_DESKTOP"
    
    # Kiểm tra Python và thư viện
    echo -n "Kiểm tra Python và thư viện tkinter: "
    if python3 -c "import tkinter" 2>/dev/null; then
        echo "OK"
    else
        echo "LỖI - Tkinter không được cài đặt"
        echo "  Vui lòng cài đặt với: sudo apt-get install python3-tk"
    fi
    
    echo "===== HOÀN TẤT KIỂM TRA ====="
}

# Xử lý tham số dòng lệnh
case "$1" in
    --launch)
        launch_auth_interface
        ;;
    --monitor-lock)
        monitor_lock_screen
        ;;
    *)
        show_menu
        ;;
esac