#!/bin/bash

# Script để khởi động face authentication service một cách an toàn
# Script này nên được thêm vào /etc/xdg/autostart hoặc chạy bởi service systemd

# Đợi đến khi dịch vụ hiển thị đồ họa sẵn sàng (khoảng 5 giây)
sleep 5

# Đảm bảo DISPLAY được thiết lập
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

# Cho phép truy cập X server cho người dùng hiện tại
xhost +si:localuser:$(whoami)

# Đảm bảo quyền truy cập camera
for cam in /dev/video*; do
    if [ -e "$cam" ]; then
        # Thử thiết lập quyền với sudo nếu có thể
        sudo chmod 666 "$cam" 2>/dev/null || true
        sudo chgrp video "$cam" 2>/dev/null || true
    fi
done

# Kiểm tra xem giao diện khóa màn hình có đang chạy không
if ! pgrep -f "lockscreen_integration.sh --monitor-lock" >/dev/null; then
    echo "Khởi động face authentication monitor..."
    /bin/bash /home/izzy/Documents/face_authentication_linux/lockscreen_integration.sh --monitor-lock &
fi

exit 0