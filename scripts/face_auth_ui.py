#!/usr/bin/env python3
import sys
import cv2
import pickle
import face_recognition
import numpy as np
import os
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QProgressBar, QFrame, QMessageBox)
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread

# Import the authentication function from face_auth.py
from face_auth import authenticate_face, get_face_auth_model

class FaceDetectionThread(QThread):
    update_frame = pyqtSignal(np.ndarray, list)
    auth_progress = pyqtSignal(int, int)  # successful_attempts, total_attempts
    auth_result = pyqtSignal(bool)

    def __init__(self, username, model_path, confidence_threshold):
        super().__init__()
        self.username = username
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.running = True

    def run(self):
        # Load model
        try:
            with open(self.model_path, 'rb') as f:
                clf, _, _ = pickle.load(f)
        except Exception as e:
            self.auth_result.emit(False)
            return

        # Initialize camera
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.auth_result.emit(False)
            return
        
        # Wait for camera to initialize
        time.sleep(1)
        
        # Authentication variables
        max_attempts = 5
        successful_attempts = 0
        total_attempts = 0
        
        while self.running and total_attempts < max_attempts:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Find faces and encode
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            # Send frame and face locations to UI
            self.update_frame.emit(frame, face_locations)
            
            if len(face_locations) > 0:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                
                for face_encoding in face_encodings:
                    # Predict user and confidence
                    predictions = clf.predict_proba([face_encoding])[0]
                    best_match_index = np.argmax(predictions)
                    confidence = predictions[best_match_index]
                    predicted_user = clf.classes_[best_match_index]
                    
                    # Check if predicted user matches login user
                    total_attempts += 1
                    if predicted_user == self.username and confidence >= self.confidence_threshold:
                        successful_attempts += 1
                    
                    # Update progress
                    self.auth_progress.emit(successful_attempts, total_attempts)
                    break
                
                # Pause between attempts
                time.sleep(0.2)
            
        cap.release()
        
        # Authentication is successful if at least 3/5 attempts are successful
        self.auth_result.emit(successful_attempts >= 3)

    def stop(self):
        self.running = False
        self.wait()


class FaceAuthUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Authentication")
        self.setMinimumSize(800, 600)
        
        # Create the login screen
        self.init_login_screen()
        
        # Set default model path
        self.model_path = "models/face_auth_model.pkl"
        self.confidence_threshold = 0.6

    def init_login_screen(self):
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Title
        title_label = QLabel("Face Authentication")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Face icon (placeholder - you can replace with an actual face icon)
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        # You can add an actual icon here with: icon_label.setPixmap(QPixmap("path/to/face_icon.png"))
        main_layout.addWidget(icon_label)
        
        # Username input
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        username_label.setFont(QFont("Arial", 12))
        self.username_input = QLineEdit()
        self.username_input.setMinimumWidth(200)
        self.username_input.setFont(QFont("Arial", 12))
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        
        # Add username layout to main layout
        form_widget = QWidget()
        form_widget.setLayout(username_layout)
        main_layout.addWidget(form_widget)
        
        # Login button
        self.login_button = QPushButton("Login with Face ID")
        self.login_button.setFont(QFont("Arial", 12))
        self.login_button.setMinimumHeight(40)
        self.login_button.clicked.connect(self.start_face_auth)
        main_layout.addWidget(self.login_button)

    def init_scanning_screen(self):
        # Clear current widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Scanning Face")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Status label
        self.status_label = QLabel("Looking for your face...")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Camera view
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setFrameShape(QFrame.Box)
        main_layout.addWidget(self.camera_label)
        
        # Progress indicators
        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 5)  # 5 attempts
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Scan progress: %v/%m")
        self.progress_bar.setMinimumWidth(300)
        
        progress_layout.addWidget(self.progress_bar)
        progress_widget = QWidget()
        progress_widget.setLayout(progress_layout)
        main_layout.addWidget(progress_widget)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_auth)
        main_layout.addWidget(self.cancel_button)

    def start_face_auth(self):
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Input Error", "Please enter a username")
            return
            
        # Check if model exists
        if not os.path.exists(self.model_path):
            QMessageBox.critical(self, "Model Error", "Face authentication model not found!")
            return
            
        # Initialize scanning screen
        self.init_scanning_screen()
        
        # Start face detection thread
        self.detection_thread = FaceDetectionThread(
            username, self.model_path, self.confidence_threshold
        )
        self.detection_thread.update_frame.connect(self.update_camera_view)
        self.detection_thread.auth_progress.connect(self.update_progress)
        self.detection_thread.auth_result.connect(self.show_auth_result)
        self.detection_thread.start()

    def update_camera_view(self, frame, face_locations):
        # Draw rectangles around detected faces
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            
        # Convert to Qt format for display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # Resize to fit the label if needed
        pixmap = pixmap.scaled(self.camera_label.width(), self.camera_label.height(), 
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.camera_label.setPixmap(pixmap)
        
        # Update status based on face detection
        if face_locations:
            self.status_label.setText("Face detected! Verifying...")
        else:
            self.status_label.setText("Position your face in the camera")

    def update_progress(self, successful_attempts, total_attempts):
        self.progress_bar.setValue(total_attempts)
        self.progress_bar.setFormat(f"Progress: {total_attempts}/5 (Matches: {successful_attempts})")

    def show_auth_result(self, success):
        # Stop the detection thread
        if hasattr(self, 'detection_thread'):
            self.detection_thread.stop()
            
        if success:
            QMessageBox.information(self, "Authentication Successful", 
                                   "Face verification complete! You are now logged in.")
            # Here you would typically proceed to the main application
        else:
            QMessageBox.critical(self, "Authentication Failed", 
                                "Could not verify your identity. Please try again.")
            # Return to login screen
            self.init_login_screen()

    def cancel_auth(self):
        if hasattr(self, 'detection_thread'):
            self.detection_thread.stop()
        self.init_login_screen()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FaceAuthUI()
    window.show()
    sys.exit(app.exec_())
