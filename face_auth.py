#!/usr/bin/env python3
import cv2
import numpy as np
import face_recognition
import os
import time
import json
import logging
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/var/log/face-auth.log'
)
logger = logging.getLogger('face-auth')

class FaceAuth:
    def __init__(self, data_dir=None):
        # Thư mục lưu trữ dữ liệu khuôn mặt
        if data_dir is None:
            self.data_dir = Path.home() / '.face-auth'
        else:
            self.data_dir = Path(data_dir)

        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(self.data_dir, exist_ok=True)
        os.chmod(self.data_dir, 0o700)  # Chỉ người dùng hiện tại có quyền truy cập

        # Các thông số chống giả mạo
        self.EAR_THRESHOLD = 0.25
        self.REQUIRED_BLINKS = 2
        self.SHARPNESS_THRESHOLD = 50
        self.FACE_MATCH_THRESHOLD = 0.5  # Ngưỡng khoảng cách Euclidean thấp hơn = giống nhau hơn
        self.MIN_VERIFICATION_DURATION = 3
        self.MIN_EYE_CLOSED_FRAMES = 2
        self.MAX_EYE_CLOSED_FRAMES = 10

    def calculate_ear(self, eye):
        """Tính tỷ lệ khía cạnh mắt (EAR)"""
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        return (A + B) / (2.0 * C)

    def register_face(self, username):
        """Đăng ký khuôn mặt cho người dùng"""
        try:
            # Kiểm tra xem người dùng tồn tại không (theo Linux)
            if not self._user_exists(username):
                logger.error(f"User {username} does not exist")
                return False, "Người dùng không tồn tại"

            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                logger.error("Cannot open camera")
                return False, "Không thể mở camera"
            
            # Điều chỉnh cài đặt camera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Các biến cho phát hiện live
            blink_count = 0
            eye_closed_frames = 0
            eye_open_frames = 0
            face_verified = False
            start_time = time.time()
            encoded_face = None
            
            print("Nhìn vào camera và chớp mắt vài lần để xác thực khuôn mặt sống")
            print("Nhấn 's' để lưu hoặc 'q' để thoát")
            
            # Thông tin trạng thái
            status_text = "Đang chuẩn bị..."
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Phát hiện khuôn mặt
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if not face_locations:
                    status_text = "Không tìm thấy khuôn mặt"
                    print("\r" + status_text, end="")
                    continue
                
                # Kiểm tra độ sắc nét để chống photo giả mạo
                top, right, bottom, left = face_locations[0]
                face_crop = gray[top:bottom, left:right]
                sharpness = cv2.Laplacian(face_crop, cv2.CV_64F).var()
                
                if sharpness < self.SHARPNESS_THRESHOLD:
                    status_text = "Độ sắc nét thấp - nghi ngờ photo"
                    print("\r" + status_text, end="")
                    continue
                
                # Phát hiện landmark khuôn mặt 
                face_landmarks = face_recognition.face_landmarks(rgb_frame, face_locations)
                
                if face_landmarks:
                    # Tính EAR (Eye Aspect Ratio)
                    left_eye = np.array(face_landmarks[0]['left_eye'])
                    right_eye = np.array(face_landmarks[0]['right_eye'])
                    
                    # Tính EAR cho cả hai mắt
                    left_ear = self.calculate_ear(left_eye)
                    right_ear = self.calculate_ear(right_eye)
                    ear = (left_ear + right_ear) / 2.0
                    
                    # Phát hiện chớp mắt
                    if ear < self.EAR_THRESHOLD:
                        eye_closed_frames += 1
                        eye_open_frames = 0
                    else:
                        eye_open_frames += 1
                        # Nếu mắt được mở sau khi đóng, đếm như một lần chớp
                        if eye_closed_frames >= self.MIN_EYE_CLOSED_FRAMES and eye_open_frames > 3:
                            blink_count += 1
                            eye_closed_frames = 0
                            status_text = f"Phát hiện {blink_count} lần chớp mắt"
                            print("\r" + status_text, end="")
                
                # Mã hóa khuôn mặt
                if blink_count >= self.REQUIRED_BLINKS:
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    if face_encodings:
                        encoded_face = face_encodings[0]
                        face_verified = True
                        status_text = "Đã xác thực khuôn mặt - Nhấn 's' để lưu"
                        print("\r" + status_text, end="")
                
                # Kiểm tra phím
                key = cv2.waitKey(1) & 0xFF
                if key == ord('s') and face_verified:
                    # Lưu face encoding
                    self._save_face_encoding(username, encoded_face)
                    cap.release()
                    return True, "Đã đăng ký khuôn mặt thành công"
                
                elif key == ord('q'):
                    cap.release()
                    return False, "Đã hủy đăng ký"
                
                # Hiển thị trạng thái mới
                print("\r" + status_text, end="")
                
            cap.release()
            
        except Exception as e:
            logger.error(f"Error during face registration: {str(e)}")
            return False, f"Lỗi: {str(e)}"

    def verify_face(self, username):
        """Xác thực khuôn mặt người dùng"""
        try:
            # Kiểm tra xem người dùng đã đăng ký khuôn mặt chưa
            if not self._has_registered_face(username):
                logger.error(f"User {username} has not registered a face")
                return False, "Người dùng chưa đăng ký khuôn mặt"
            
            # Lấy face encoding đã lưu
            stored_encoding = self._load_face_encoding(username)
            if stored_encoding is None:
                return False, "Không thể tải thông tin khuôn mặt"
            
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                logger.error("Cannot open camera")
                return False, "Không thể mở camera"
            
            # Điều chỉnh cài đặt camera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Các biến cho phát hiện live
            blink_count = 0
            eye_closed_frames = 0
            eye_open_frames = 0
            face_verified = False
            start_time = time.time()
            frame_counter = 0
            
            print("Nhìn vào camera và chớp mắt để xác thực")
            
            # Thông tin trạng thái
            status_text = "Đang chuẩn bị..."
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                
                frame_counter += 1
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Phát hiện khuôn mặt
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if not face_locations:
                    status_text = "Không tìm thấy khuôn mặt"
                    print("\r" + status_text, end="")
                    time.sleep(0.1)
                    continue
                
                # Kiểm tra độ sắc nét để chống photo giả mạo
                top, right, bottom, left = face_locations[0]
                face_crop = gray[top:bottom, left:right]
                sharpness = cv2.Laplacian(face_crop, cv2.CV_64F).var()
                
                if sharpness < self.SHARPNESS_THRESHOLD:
                    status_text = "Độ sắc nét thấp - nghi ngờ photo"
                    print("\r" + status_text, end="")
                    time.sleep(0.1)
                    continue
                
                # Phát hiện landmark khuôn mặt 
                face_landmarks = face_recognition.face_landmarks(rgb_frame, face_locations)
                
                if face_landmarks:
                    # Tính EAR (Eye Aspect Ratio)
                    left_eye = np.array(face_landmarks[0]['left_eye'])
                    right_eye = np.array(face_landmarks[0]['right_eye'])
                    
                    # Tính EAR cho cả hai mắt
                    left_ear = self.calculate_ear(left_eye)
                    right_ear = self.calculate_ear(right_eye)
                    ear = (left_ear + right_ear) / 2.0
                    
                    # Phát hiện chớp mắt
                    if ear < self.EAR_THRESHOLD:
                        eye_closed_frames += 1
                        eye_open_frames = 0
                    else:
                        eye_open_frames += 1
                        # Nếu mắt được mở sau khi đóng, đếm như một lần chớp
                        if eye_closed_frames >= self.MIN_EYE_CLOSED_FRAMES and eye_open_frames > 3:
                            blink_count += 1
                            eye_closed_frames = 0
                            status_text = f"Phát hiện {blink_count} lần chớp mắt"
                            print("\r" + status_text, end="")
                
                # Mã hóa và so sánh khuôn mặt
                if frame_counter % 5 == 0:  # Làm mỗi 5 frame để giảm tải
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    if face_encodings:
                        current_encoding = face_encodings[0]
                        # Tính khoảng cách Euclidean
                        distance = np.linalg.norm(current_encoding - stored_encoding)
                        
                        if distance < self.FACE_MATCH_THRESHOLD:
                            face_verified = True
                            status_text = f"Khuôn mặt khớp (độ tin cậy: {1-distance:.2f})"
                        else:
                            face_verified = False
                            status_text = f"Khuôn mặt không khớp (khoảng cách: {distance:.2f})"
                
                # Kiểm tra điều kiện thành công
                verification_duration = time.time() - start_time
                if (
                    blink_count >= self.REQUIRED_BLINKS and
                    face_verified and
                    verification_duration >= self.MIN_VERIFICATION_DURATION
                ):
                    cap.release()
                    return True, "Xác thực thành công"
                
                # Nếu quá lâu mà không thành công, thoát
                if verification_duration > 15:
                    cap.release()
                    return False, "Hết thời gian xác thực"
                
                # Hiển thị trạng thái mới
                print("\r" + status_text, end="")
                
                # Kiểm tra phím thoát
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cap.release()
            return False, "Đã hủy xác thực"
            
        except Exception as e:
            logger.error(f"Error during face verification: {str(e)}")
            return False, f"Lỗi: {str(e)}"

    def _save_face_encoding(self, username, encoding):
        """Lưu face encoding cho người dùng"""
        encoding_file = self.data_dir / f"{username}.json"
        data = {
            "encoding": encoding.tolist(),
            "timestamp": time.time()
        }
        with open(encoding_file, 'w') as f:
            json.dump(data, f)
        # Đặt quyền truy cập chỉ cho người dùng
        os.chmod(encoding_file, 0o600)
        logger.info(f"Face encoding saved for user {username}")

    def _load_face_encoding(self, username):
        """Tải face encoding của người dùng"""
        encoding_file = self.data_dir / f"{username}.json"
        try:
            with open(encoding_file, 'r') as f:
                data = json.load(f)
            return np.array(data["encoding"])
        except Exception as e:
            logger.error(f"Error loading face encoding for {username}: {str(e)}")
            return None

    def _has_registered_face(self, username):
        """Kiểm tra người dùng đã đăng ký khuôn mặt chưa"""
        encoding_file = self.data_dir / f"{username}.json"
        return encoding_file.exists()

    def _user_exists(self, username):
        """Kiểm tra người dùng có tồn tại trong hệ thống không"""
        try:
            import pwd
            pwd.getpwnam(username)
            return True
        except KeyError:
            return False
