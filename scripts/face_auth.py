#!/usr/bin/env python3
import cv2
import pickle
import face_recognition
import numpy as np
import argparse
import os
import time

def authenticate_face(username, model_path="models/face_auth_model.pkl", confidence_threshold=0.6):
    # Kiểm tra xem model có tồn tại hay không
    if not os.path.exists(model_path):
        print("FAILURE: Model không tồn tại")
        return False
    
    # Tải model
    try:
        with open(model_path, 'rb') as f:
            clf, _, _ = pickle.load(f)
    except Exception as e:
        print(f"FAILURE: Không thể tải model: {e}")
        return False
    
    # Khởi tạo camera - sử dụng camera với chỉ số 1 thay vì 0
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Không thể mở camera với index 1! Thử với index 2...")
        cap = cv2.VideoCapture(2)  # Thử với camera thứ 2 nếu camera thứ 1 không mở được
        if not cap.isOpened():
            print("FAILURE: Không thể mở camera nào!")
            return False
    
    # Đợi camera khởi động
    time.sleep(1)
    
    # Lấy 5 khung hình để xác thực
    max_attempts = 5
    successful_attempts = 0
    
    for _ in range(max_attempts):
        ret, frame = cap.read()
        if not ret:
            continue
        
        # Tìm khuôn mặt và mã hóa
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if len(face_locations) == 0:
            continue
        
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        for face_encoding in face_encodings:
            # Dự đoán người dùng và độ tin cậy
            predictions = clf.predict_proba([face_encoding])[0]
            best_match_index = np.argmax(predictions)
            confidence = predictions[best_match_index]
            predicted_user = clf.classes_[best_match_index]
            
            # Kiểm tra xem người dùng dự đoán có khớp với người dùng đăng nhập không
            if predicted_user == username and confidence >= confidence_threshold:
                successful_attempts += 1
                break
        
        # Nghỉ giữa các lần thử
        time.sleep(0.2)
    
    cap.release()
    
    # Xác thực thành công nếu có ít nhất 3/5 lần thử thành công
    if successful_attempts >= 3:
        print("SUCCESS")
        return True
    else:
        print("FAILURE")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Xác thực khuôn mặt")
    parser.add_argument("--username", required=True, help="Tên người dùng để xác thực")
    parser.add_argument("--model", default="models/face_auth_model.pkl", help="Đường dẫn đến file model")
    parser.add_argument("--threshold", type=float, default=0.6, help="Ngưỡng độ tin cậy")
    args = parser.parse_args()
    
    authenticate_face(args.username, args.model, args.threshold)
