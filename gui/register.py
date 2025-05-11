#!/usr/bin/env python3
import sys
import os

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append("..")

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QPushButton, QLabel, QLineEdit, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
import cv2
from scripts.collect_faces import FaceCollector
from scripts.train_model import train_face_model

class FaceRegistrationThread(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, username, num_samples):
        super().__init__()
        self.username = username
        self.num_samples = num_samples
        
    def run(self):
        # Không cần dùng thread nữa, sẽ mở cửa sổ FaceCollector trực tiếp từ GUI
        pass

class RegisterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Đăng ký khuôn mặt')
        self.setFixedSize(400, 300)
        
        # Widget chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Tiêu đề
        title = QLabel('Đăng ký khuôn mặt mới')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 18px; font-weight: bold; margin: 10px;')
        layout.addWidget(title)
        
        # Nhập tên người dùng
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Nhập tên người dùng')
        layout.addWidget(self.username_input)
        
        # Nút đăng ký
        self.register_btn = QPushButton('Bắt đầu đăng ký')
        self.register_btn.clicked.connect(self.start_registration)
        layout.addWidget(self.register_btn)
        
        # Label hiển thị trạng thái
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Thêm khoảng trống
        layout.addStretch()
        
    def start_registration(self):
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, 'Lỗi', 'Vui lòng nhập tên người dùng!')
            return
            
        self.register_btn.setEnabled(False)
        self.status_label.setText('Đang chuẩn bị...')
        
        # Mở cửa sổ thu thập khuôn mặt
        self.face_collector_window = FaceCollector(username, 40)
        self.face_collector_window.show()
        self.register_btn.setEnabled(True)
        self.status_label.setText('Đang thu thập dữ liệu khuôn mặt...')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RegisterWindow()
    window.show()
    sys.exit(app.exec_()) 