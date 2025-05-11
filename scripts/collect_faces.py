#!/usr/bin/env python3
import cv2
import os
import time
import argparse
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtGui import QImage, QPixmap
import sys
from scripts.train_model import train_face_model

class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage)
    face_detected = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.running = True
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.last_frame = None

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Không thể mở camera!")
            return

        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("Không thể đọc khung hình!")
                break
            self.last_frame = frame.copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.frame_ready.emit(qt_image)
            self.face_detected.emit(len(faces) > 0)

            time.sleep(0.03)  # Limit frame rate

        cap.release()

    def stop(self):
        self.running = False
        self.wait()

class FaceCollector(QMainWindow):
    def __init__(self, username, num_samples=40, output_dir="data"):
        super().__init__()
        self.username = username
        self.num_samples = num_samples
        self.output_dir = output_dir
        self.count = 0
        self.setup_ui()
        self.setup_camera()

    def setup_ui(self):
        self.setWindowTitle("Thu thập dữ liệu khuôn mặt")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create image label
        self.image_label = QLabel()
        self.image_label.setMinimumSize(640, 480)
        layout.addWidget(self.image_label)

        # Create status label
        self.status_label = QLabel("Nhấn 's' để bắt đầu thu thập dữ liệu...")
        layout.addWidget(self.status_label)

    def setup_camera(self):
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self.update_frame)
        self.camera_thread.face_detected.connect(self.handle_face_detected)
        self.camera_thread.start()

    def update_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        ))

    def handle_face_detected(self, detected):
        if detected and self.count < self.num_samples:
            self.save_face()
            self.count += 1
            self.status_label.setText(f"Đã thu thập {self.count}/{self.num_samples} hình ảnh")
            
            # Khi đủ số lượng ảnh
            if self.count >= self.num_samples:
                self.status_label.setText("Đã thu thập đủ ảnh! Đang huấn luyện mô hình...")
                try:
                    # Huấn luyện mô hình
                    model_path = train_face_model()
                    QMessageBox.information(self, "Thành công", 
                        f"Đã thu thập đủ {self.num_samples} ảnh cho {self.username}!\nMô hình đã được huấn luyện thành công.")
                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Lỗi khi huấn luyện mô hình: {str(e)}")
                finally:
                    # Đóng cửa sổ
                    self.close()

    def save_face(self):
        user_dir = os.path.join(self.output_dir, self.username)
        os.makedirs(user_dir, exist_ok=True)
        frame = self.camera_thread.last_frame
        if frame is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.camera_thread.face_cascade.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in faces:
                face_img = frame[y:y+h, x:x+w]
                img_path = os.path.join(user_dir, f"{self.username}_{self.count}.jpg")
                cv2.imwrite(img_path, face_img)
                break

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_S:
            self.status_label.setText("Đang thu thập dữ liệu...")
        elif event.key() == Qt.Key_Q:
            self.close()

    def closeEvent(self, event):
        self.camera_thread.stop()
        event.accept()

def main():
    parser = argparse.ArgumentParser(description="Thu thập dữ liệu khuôn mặt")
    parser.add_argument("--username", required=True, help="Tên người dùng")
    parser.add_argument("--samples", type=int, default=20, help="Số lượng mẫu cần thu thập")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = FaceCollector(args.username, args.samples)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
