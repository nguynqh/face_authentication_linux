#!/usr/bin/env python3
import sys
import os

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QPushButton, QLabel, QMessageBox, QStackedWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
import cv2
from scripts.authenticate import authenticate_face

class AuthenticationThread(QThread):
    finished = pyqtSignal(bool, str)
    
    def run(self):
        try:
            username = authenticate_face()
            if username:
                self.finished.emit(True, username)
            else:
                self.finished.emit(False, "Không nhận diện được khuôn mặt!")
        except Exception as e:
            self.finished.emit(False, f"Lỗi: {str(e)}")

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Đăng nhập bằng khuôn mặt')
        self.setFixedSize(400, 300)
        
        # Widget chính
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Trang đăng nhập khuôn mặt
        self.face_login_page = QWidget()
        face_layout = QVBoxLayout(self.face_login_page)
        
        # Tiêu đề
        title = QLabel('Đăng nhập bằng khuôn mặt')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 18px; font-weight: bold; margin: 10px;')
        face_layout.addWidget(title)
        
        # Nút đăng nhập
        self.login_btn = QPushButton('Bắt đầu xác thực')
        self.login_btn.clicked.connect(self.start_authentication)
        face_layout.addWidget(self.login_btn)
        
        # Label hiển thị trạng thái
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        face_layout.addWidget(self.status_label)
        
        # Nút chuyển sang đăng nhập mật khẩu
        self.switch_btn = QPushButton('Chuyển sang đăng nhập mật khẩu')
        self.switch_btn.clicked.connect(self.switch_to_password)
        face_layout.addWidget(self.switch_btn)
        
        # Thêm khoảng trống
        face_layout.addStretch()
        
        # Trang đăng nhập mật khẩu
        self.password_page = QWidget()
        password_layout = QVBoxLayout(self.password_page)
        
        # Tiêu đề
        password_title = QLabel('Đăng nhập bằng mật khẩu')
        password_title.setAlignment(Qt.AlignCenter)
        password_title.setStyleSheet('font-size: 18px; font-weight: bold; margin: 10px;')
        password_layout.addWidget(password_title)
        
        # Nút quay lại
        back_btn = QPushButton('Quay lại đăng nhập khuôn mặt')
        back_btn.clicked.connect(self.switch_to_face)
        password_layout.addWidget(back_btn)
        
        # Thêm khoảng trống
        password_layout.addStretch()
        
        # Thêm các trang vào stacked widget
        self.central_widget.addWidget(self.face_login_page)
        self.central_widget.addWidget(self.password_page)
        
    def start_authentication(self):
        self.login_btn.setEnabled(False)
        self.status_label.setText('Đang xác thực...')
        
        # Tạo và chạy thread xác thực
        self.auth_thread = AuthenticationThread()
        self.auth_thread.finished.connect(self.authentication_finished)
        self.auth_thread.start()
        
    def authentication_finished(self, success, message):
        self.login_btn.setEnabled(True)
        
        if success:
            self.status_label.setText(f'Xác thực thành công! Chào mừng {message}')
            QMessageBox.information(self, 'Thành công', f'Đăng nhập thành công! Chào mừng {message}')
            # TODO: Thực hiện đăng nhập vào hệ thống
        else:
            self.status_label.setText(message)
            QMessageBox.warning(self, 'Lỗi', message)
            
    def switch_to_password(self):
        self.central_widget.setCurrentWidget(self.password_page)
        
    def switch_to_face(self):
        self.central_widget.setCurrentWidget(self.face_login_page)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_()) 