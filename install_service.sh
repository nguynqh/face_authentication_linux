#!/bin/bash

# Tạo thư mục systemd nếu chưa tồn tại
sudo mkdir -p /etc/systemd/system

# Copy service file
sudo cp face-auth.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable face-auth.service

echo "Service đã được cài đặt. Bạn có thể khởi động service bằng lệnh:"
echo "sudo systemctl start face-auth.service"
echo ""
echo "Để kiểm tra trạng thái service:"
echo "sudo systemctl status face-auth.service" 