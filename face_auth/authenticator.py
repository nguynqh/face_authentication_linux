import cv2
import dlib
import time
import os
import platform
import numpy as np
import face_recognition
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/var/log/face-auth.log'
)
logger = logging.getLogger('face-auth-authenticator')

class FaceAuthenticator:
    def __init__(self, username, callback=None):
        self.username = username.strip()
        self.callback = callback  # Callback để cập nhật trạng thái UI
        self.face_id_file = os.path.join("/var/lib/face-auth", f"{self.username}.txt")
        self.result = {"status": "unknown", "message": "Not started yet"}

    def notify_status(self, status, message):
        """Cập nhật trạng thái và gửi về UI nếu có callback"""
        self.result = {"status": status, "message": message}
        logger.info(f"Authentication status: {status}, Message: {message}")
        if self.callback:
            self.callback(status, message)

    def authenticate(self):
        if not os.path.exists(self.face_id_file):
            self.notify_status("fail", "No Face ID registered")
            return False

        try:
            with open(self.face_id_file, "rb") as f:
                stored_encoding = np.frombuffer(f.read(), dtype=np.float64)

            if stored_encoding.shape != (128,) or np.all(stored_encoding == 0):
                self.notify_status("fail", "Invalid Face ID data")
                return False

            # Camera initialization based on OS
            system_platform = platform.system()
            if system_platform == "Windows":
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

            # Thiết lập thêm các tham số để tăng độ ổn định
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

            if not cap.isOpened():
                self.notify_status("fail", "Cannot access camera")
                return False

            # Thông báo đã bắt đầu xác thực
            self.notify_status("processing", "Starting face authentication...")

            detector = dlib.get_frontal_face_detector()
            predictor_path = "/usr/share/face-auth/shape_predictor_68_face_landmarks.dat"
            predictor = dlib.shape_predictor(predictor_path)

            def shape_to_np(shape):
                coords = np.zeros((68, 2), dtype=int)
                for i in range(68):
                    coords[i] = (shape.part(i).x, shape.part(i).y)
                return coords

            def calculate_ear(eye):
                A = np.linalg.norm(eye[1] - eye[5])
                B = np.linalg.norm(eye[2] - eye[4])
                C = np.linalg.norm(eye[0] - eye[3])
                return (A + B) / (2.0 * C)

            # Thông số cấu hình
            EAR_THRESHOLD = 0.25
            REQUIRED_BLINKS = 3  # Giảm để trải nghiệm tốt hơn
            SHARPNESS_THRESHOLD = 100
            FACE_MATCH_THRESHOLD = 0.5
            MIN_VERIFICATION_DURATION = 5  # Giảm để trải nghiệm tốt hơn
            MIN_EYE_CLOSED_FRAMES = 3
            MAX_NO_MOVEMENT = 20

            blink_count = 0
            eye_closed_frames = 0
            eye_blinking = False
            face_verified = False
            start_time = time.time()
            frame_counter = 0
            blink_timestamps = []
            no_movement_frames = 0

            while True:
                # Kiểm tra thời gian tối đa
                if time.time() - start_time > 30:  # Tối đa 30 giây
                    self.notify_status("fail", "Authentication timeout")
                    cap.release()
                    return False

                ret, frame = cap.read()
                if not ret:
                    continue

                frame = cv2.resize(frame, (640, 480))
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_counter += 1

                # Cập nhật UI với frame hiện tại nếu có callback
                if self.callback and callable(getattr(self.callback, "update_frame", None)):
                    self.callback.update_frame(frame)

                face_locations = face_recognition.face_locations(rgb)
                if not face_locations:
                    no_movement_frames += 1
                    self.notify_status("processing", "No face detected, please look at the camera")
                    continue

                no_movement_frames = 0
                top, right, bottom, left = face_locations[0]
                face_crop = gray[top:bottom, left:right]
                
                # Cập nhật thông báo
                self.notify_status("processing", "Face detected, verifying...")
                
                # Kiểm tra độ sắc nét
                sharpness = cv2.Laplacian(face_crop, cv2.CV_64F).var()
                if sharpness < SHARPNESS_THRESHOLD:
                    self.notify_status("fail", "Blurry image detected")
                    cap.release()
                    return False

                # Phát hiện chớp mắt
                rects = detector(gray, 0)
                if rects:
                    shape = predictor(gray, rects[0])
                    shape = shape_to_np(shape)
                    leftEye = shape[42:48]
                    rightEye = shape[36:42]
                    ear = (calculate_ear(leftEye) + calculate_ear(rightEye)) / 2.0

                    if ear < EAR_THRESHOLD:
                        eye_closed_frames += 1
                        eye_blinking = True
                        self.notify_status("processing", "Blink detected...")
                    else:
                        if eye_blinking:
                            if eye_closed_frames >= MIN_EYE_CLOSED_FRAMES:
                                now = time.time()
                                if len(blink_timestamps) == 0 or now - blink_timestamps[-1] > 1.0:
                                    blink_count += 1
                                    blink_timestamps.append(now)
                                    self.notify_status("processing", f"Blink count: {blink_count}/{REQUIRED_BLINKS}")
                            eye_closed_frames = 0
                            eye_blinking = False

                # Xác thực khuôn mặt
                if frame_counter % 5 == 0:
                    face_encodings = face_recognition.face_encodings(rgb, face_locations)
                    if face_encodings:
                        current_encoding = face_encodings[0]
                        distance = np.linalg.norm(current_encoding - stored_encoding)

                        if distance < FACE_MATCH_THRESHOLD:
                            face_verified = True
                            self.notify_status("processing", "Face matched, continue verifying...")
                        else:
                            self.notify_status("fail", "Face ID does not match")
                            cap.release()
                            return False

                # Kiểm tra hoàn thành các điều kiện
                verification_duration = time.time() - start_time
                if verification_duration >= MIN_VERIFICATION_DURATION:
                    if blink_count >= REQUIRED_BLINKS and face_verified:
                        self.notify_status("success", "Face ID verified successfully")
                        cap.release()
                        return True
                    elif verification_duration >= 20:  # Nếu quá 20 giây mà chưa đủ điều kiện
                        if blink_count < REQUIRED_BLINKS:
                            self.notify_status("fail", f"Not enough blinks detected ({blink_count}/{REQUIRED_BLINKS})")
                        elif not face_verified:
                            self.notify_status("fail", "Face verification failed")
                        cap.release()
                        return False

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            self.notify_status("fail", f"Error: {str(e)}")
            return False

        self.notify_status("fail", "Authentication process interrupted")
        return False
