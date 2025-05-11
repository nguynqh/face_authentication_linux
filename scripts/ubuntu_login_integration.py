#!/usr/bin/env python3
import os
import sys
import subprocess
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from gui.login import LoginWindow

class UbuntuLoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        # Thiết lập cửa sổ toàn màn hình
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()
        
        # Widget chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Thêm cửa sổ đăng nhập
        self.login_window = LoginWindow()
        layout.addWidget(self.login_window)
        
    def keyPressEvent(self, event):
        # Cho phép thoát bằng Alt+F4
        if event.key() == Qt.Key_F4 and event.modifiers() == Qt.AltModifier:
            self.close()

def main():
    # Kiểm tra quyền root
    if os.geteuid() != 0:
        print("Script này cần chạy với quyền root!")
        sys.exit(1)
        
    # Tắt màn hình đăng nhập mặc định
    subprocess.run(['systemctl', 'stop', 'gdm'])
    
    # Khởi tạo ứng dụng
    app = QApplication(sys.argv)
    window = UbuntuLoginWindow()
    window.show()
    
    # Chạy ứng dụng
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 