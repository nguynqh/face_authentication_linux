#!/usr/bin/env python3
import face_recognition
import cv2
import pickle
import os
import numpy as np

def authenticate_face(model_path="data/face_model.pkl", threshold=0.6):
    # Load mô hình đã huấn luyện
    try:
        with open(model_path, 'rb') as f:
            known_face_encodings = pickle.load(f)
    except Exception as e:
        print(f"Lỗi khi đọc mô hình: {str(e)}")
        return None

    # Khởi tạo camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Không thể mở camera!")
        return None

    print("Đang xác thực khuôn mặt...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Không thể đọc khung hình!")
            break

        # Tìm khuôn mặt trong khung hình
        face_locations = face_recognition.face_locations(frame)
        if not face_locations:
            cv2.imshow("Face Authentication", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        # Mã hóa khuôn mặt tìm thấy
        face_encoding = face_recognition.face_encodings(frame, face_locations)[0]

        # So sánh với các khuôn mặt đã biết
        matches = []
        for username, known_encoding in known_face_encodings.items():
            distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
            if distance < threshold:
                matches.append((username, distance))

        # Vẽ khung xung quanh khuôn mặt
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        # Hiển thị kết quả
        if matches:
            # Lấy kết quả tốt nhất
            best_match = min(matches, key=lambda x: x[1])
            username, confidence = best_match
            confidence = 1 - confidence  # Chuyển đổi khoảng cách thành độ tin cậy
            
            # Hiển thị tên người dùng và độ tin cậy
            text = f"{username} ({confidence:.2f})"
            cv2.putText(frame, text, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.imshow("Face Authentication", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            # Nếu độ tin cậy đủ cao, trả về tên người dùng
            if confidence > 0.7:
                cap.release()
                cv2.destroyAllWindows()
                return username
        else:
            cv2.putText(frame, "Unknown", (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.imshow("Face Authentication", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    return None

if __name__ == "__main__":
    result = authenticate_face()
    if result:
        print(f"Xác thực thành công! Chào mừng {result}")
    else:
        print("Xác thực thất bại!") 