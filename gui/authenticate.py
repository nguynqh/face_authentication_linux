#!/usr/bin/env python3
import sys
import os

# Thêm thư mục gốc vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QLabel, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
import cv2
from scripts.face_utils import load_face_model, authenticate_face

class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage)
    error_occurred = pyqtSignal(str)

    def __init__(self, known_face_encodings):
        super().__init__()
        self.running = True
        self.known_face_encodings = known_face_encodings

    def run(self):
        # Thử các index camera khác nhau
        for camera_index in [0, 1]:
            cap = cv2.VideoCapture(camera_index)
            if cap.isOpened():
                while self.running:
                    ret, frame = cap.read()
                    if ret:
                        # Chuyển đổi frame từ BGR sang RGB
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb_frame.shape
                        bytes_per_line = ch * w
                        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                        self.frame_ready.emit(qt_image)
                        
                        # Xác thực khuôn mặt
                        result = authenticate_face(frame, self.known_face_encodings)
                        if result:
                            self.error_occurred.emit(f"Xác thực thành công! Chào mừng {result}")
                            break
                    else:
                        self.error_occurred.emit(f"Không thể đọc frame từ camera {camera_index}")
                        break
                cap.release()
                return
            else:
                self.error_occurred.emit(f"Không thể mở camera {camera_index}")
        
        # Nếu không mở được camera nào
        self.error_occurred.emit("Không thể mở camera. Vui lòng kiểm tra:\n1. Camera đã được kết nối\n2. Bạn đã được thêm vào nhóm video\n3. Không có ứng dụng nào khác đang sử dụng camera")

    def stop(self):
        self.running = False
        self.wait()

class AuthenticateWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Xác thực khuôn mặt")
        self.setGeometry(100, 100, 800, 600)

        # Widget chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Label hiển thị camera
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.camera_label)

        # Label hiển thị trạng thái
        self.status_label = QLabel("Đang khởi tạo camera...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Nút đóng
        self.close_button = QPushButton("Đóng")
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)

        # Load mô hình khuôn mặt
        self.known_face_encodings = load_face_model()
        if self.known_face_encodings is None:
            QMessageBox.critical(self, "Lỗi", "Không thể tải mô hình khuôn mặt!")
            self.close()
            return

        # Khởi tạo camera thread
        self.camera_thread = CameraThread(self.known_face_encodings)
        self.camera_thread.frame_ready.connect(self.update_frame)
        self.camera_thread.error_occurred.connect(self.handle_camera_error)
        self.camera_thread.start()

    def update_frame(self, image):
        self.camera_label.setPixmap(QPixmap.fromImage(image).scaled(
            self.camera_label.size(), Qt.KeepAspectRatio))

    def handle_camera_error(self, message):
        if "Xác thực thành công" in message:
            QMessageBox.information(self, "Thành công", message)
            self.close()
        else:
            self.status_label.setText(message)

    def closeEvent(self, event):
        self.camera_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AuthenticateWindow()
    window.show()
    sys.exit(app.exec_()) 