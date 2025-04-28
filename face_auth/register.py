import cv2
import dlib
import numpy as np
import face_recognition
from imutils import face_utils
import os
import platform
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/var/log/face-auth.log'
)
logger = logging.getLogger('face-auth-register')

class FaceRegistrar:
    def __init__(self, username, callback=None):
        self.username = username
        self.callback = callback  # Callback để cập nhật trạng thái UI
        self.result = {"status": "unknown", "message": "Not started yet"}

    def notify_status(self, status, message):
        """Cập nhật trạng thái và gửi về UI nếu có callback"""
        self.result = {"status": status, "message": message}
        logger.info(f"Registration status: {status}, Message: {message}")
        if self.callback:
            self.callback(status, message)

    def encode_face(self, rgb_frame, face_locations, cropped_face=None):
        try:
            if cropped_face is not None and cropped_face.shape[0] > 0 and cropped_face.shape[1] > 0:
                face_crop_rgb = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB)
                cropped_encoding = face_recognition.face_encodings(face_crop_rgb)
                if cropped_encoding:
                    return np.array(cropped_encoding[0], dtype=np.float64).tobytes()

            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_frame, [face_locations[0]])
                if face_encodings:
                    return np.array(face_encodings[0], dtype=np.float64).tobytes()

        except Exception as e:
            self.notify_status("error", f"Encoding error: {e}")
        return None

    def register(self):
        """Đăng ký khuôn mặt cho người dùng"""
        try:
            # Kiểm tra tên người dùng hợp lệ
            if not self.username or self.username == "Unknown":
                self.notify_status("error", "Invalid username.")
                return False

            # Chuẩn bị thư mục lưu trữ
            face_data_dir = "/var/lib/face-auth"
            if not os.path.exists(face_data_dir):
                os.makedirs(face_data_dir, exist_ok=True)
                # Đặt quyền truy cập
                os.chmod(face_data_dir, 0o755)

            # Khởi tạo camera
            cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            if not cap.isOpened():
                self.notify_status("error", "Cannot open the camera.")
                return False

            # Thông báo bắt đầu
            self.notify_status("processing", "Starting face registration...")

            # Khởi tạo detector và predictor
            detector = dlib.get_frontal_face_detector()
            predictor_path = "/usr/share/face-auth/shape_predictor_68_face_landmarks.dat"
            if not os.path.exists(predictor_path):
                self.notify_status("error", "Missing predictor model file.")
                return False
            predictor = dlib.shape_predictor(predictor_path)

            # Thresholds
            sharpness_threshold = 100
            light_change_threshold = 10
            movement_threshold = 20
            min_closed_frames = 3
            required_blinks = 3  # Giảm so với gốc để dễ sử dụng hơn
            max_no_movement = 15
            max_no_light_change = 30

            blink_count = 0
            eye_closed_frames = 0
            prev_face_location = None
            no_movement_frames = 0
            no_light_change_frames = 0
            prev_light_intensity = None
            start_time = time.time()

            def calculate_ear(eye):
                A = np.linalg.norm(eye[1] - eye[5])
                B = np.linalg.norm(eye[2] - eye[4])
                C = np.linalg.norm(eye[0] - eye[3])
                return (A + B) / (2.0 * C)

            while True:
                # Kiểm tra thời gian tối đa
                if time.time() - start_time > 60:  # Tối đa 60 giây
                    self.notify_status("error", "Registration timeout")
                    cap.release()
                    return False

                ret, frame = cap.read()
                if not ret:
                    continue

                frame = cv2.resize(frame, (640, 480))
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Cập nhật UI với frame hiện tại nếu có callback
                if self.callback and callable(getattr(self.callback, "update_frame", None)):
                    self.callback.update_frame(frame)

                face_locations = face_recognition.face_locations(rgb_frame, model="hog")
                if len(face_locations) != 1:
                    self.notify_status("processing", "Please ensure only one face is visible")
                    continue

                # Cập nhật thông báo
                self.notify_status("processing", "Face detected, please blink...")

                top, right, bottom, left = face_locations[0]
                offset = 25
                top = max(0, top - offset)
                bottom = min(frame.shape[0], bottom + offset)
                left = max(0, left - offset)
                right = min(frame.shape[1], right + offset)
                face_crop = frame[top:bottom, left:right]

                # Kiểm tra độ sắc nét
                sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                if sharpness < sharpness_threshold:
                    self.notify_status("error", "Photo detected (low sharpness).")
                    cap.release()
                    return False

                # Kiểm tra thay đổi ánh sáng
                light_intensity = np.mean(gray[top:bottom, left:right])
                if prev_light_intensity is not None:
                    light_diff = abs(light_intensity - prev_light_intensity)
                    no_light_change_frames = no_light_change_frames + 1 if light_diff < light_change_threshold else 0
                    if no_light_change_frames > max_no_light_change:
                        self.notify_status("error", "No light change detected (static image).")
                        cap.release()
                        return False
                prev_light_intensity = light_intensity

                # Kiểm tra chuyển động
                if prev_face_location is not None:
                    dx = abs(prev_face_location[3] - left) + abs(prev_face_location[1] - right)
                    dy = abs(prev_face_location[0] - top) + abs(prev_face_location[2] - bottom)
                    no_movement_frames = no_movement_frames + 1 if dx < movement_threshold and dy < movement_threshold else 0
                    if no_movement_frames >= max_no_movement:
                        self.notify_status("error", "No movement detected (photo).")
                        cap.release()
                        return False
                prev_face_location = face_locations[0]

                # Phát hiện chớp mắt
                rects = detector(gray, 0)
                for rect in rects:
                    shape = predictor(gray, rect)
                    shape = face_utils.shape_to_np(shape)
                    leftEye = shape[36:42]
                    rightEye = shape[42:48]
                    ear = (calculate_ear(leftEye) + calculate_ear(rightEye)) / 2.0

                    if ear < 0.22:
                        eye_closed_frames += 1
                        self.notify_status("processing", "Blink detected...")
                    else:
                        if eye_closed_frames >= min_closed_frames:
                            blink_count += 1
                            self.notify_status("processing", f"Blink count: {blink_count}/{required_blinks}")
                        eye_closed_frames = 0

                # Kiểm tra đủ số lần chớp mắt
                if blink_count >= required_blinks:
                    # Mã hóa khuôn mặt và lưu trữ
                    face_encoding = self.encode_face(rgb_frame, face_locations, face_crop)
                    if face_encoding:
                        file_path = os.path.join(face_data_dir, f"{self.username}.txt")
                        with open(file_path, "wb") as f:
                            f.write(face_encoding)
                        
                        # Đặt quyền truy cập phù hợp
                        os.chmod(file_path, 0o644)
                        
                        # Lưu hình ảnh cho tham khảo (tùy chọn)
                        image_dir = "/var/lib/face-auth/images"
                        if not os.path.exists(image_dir):
                            os.makedirs(image_dir, exist_ok=True)
                        image_path = os.path.join(image_dir, f"{self.username}.png")
                        cv2.imwrite(image_path, face_crop)
                        
                        cap.release()
                        self.notify_status("success", "Face registered successfully.")
                        return True
                    else:
                        self.notify_status("error", "Encoding failed.")
                        cap.release()
                        return False

            cap.release()
            self.notify_status("cancelled", "Process stopped.")
            return False
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            self.notify_status("error", str(e))
            return False
