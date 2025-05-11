#!/usr/bin/env python3
import face_recognition
import cv2
import pickle
import os
import numpy as np

def load_face_model(model_path="data/face_model.pkl"):
    try:
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Lỗi khi đọc mô hình: {str(e)}")
        return None

def authenticate_face(frame, known_face_encodings, threshold=0.6):
    if known_face_encodings is None:
        return None

    # Tìm khuôn mặt trong khung hình
    face_locations = face_recognition.face_locations(frame)
    if not face_locations:
        return None

    # Mã hóa khuôn mặt tìm thấy
    face_encoding = face_recognition.face_encodings(frame, face_locations)[0]

    # So sánh với các khuôn mặt đã biết
    matches = []
    for username, known_encoding in known_face_encodings.items():
        distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
        if distance < threshold:
            matches.append((username, distance))

    # Nếu có kết quả khớp
    if matches:
        # Lấy kết quả tốt nhất
        best_match = min(matches, key=lambda x: x[1])
        username, confidence = best_match
        confidence = 1 - confidence  # Chuyển đổi khoảng cách thành độ tin cậy
        
        # Nếu độ tin cậy đủ cao, trả về tên người dùng
        if confidence > 0.7:
            return username

    return None 