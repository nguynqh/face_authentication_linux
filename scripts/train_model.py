#!/usr/bin/env python3
import face_recognition
import os
import pickle
import numpy as np
import argparse

def train_face_model(data_dir="data"):
    print("Bắt đầu huấn luyện mô hình...")
    
    # Dictionary để lưu trữ encoding của khuôn mặt
    face_encodings = {}
    
    # Duyệt qua từng thư mục người dùng
    for username in os.listdir(data_dir):
        user_dir = os.path.join(data_dir, username)
        if not os.path.isdir(user_dir):
            continue
            
        print(f"Đang xử lý dữ liệu cho {username}...")
        user_encodings = []
        
        # Đọc và mã hóa từng ảnh khuôn mặt
        for img_file in os.listdir(user_dir):
            if not img_file.endswith('.jpg'):
                continue
                
            img_path = os.path.join(user_dir, img_file)
            try:
                # Đọc ảnh và tìm khuôn mặt
                image = face_recognition.load_image_file(img_path)
                face_locations = face_recognition.face_locations(image)
                
                if face_locations:
                    # Lấy encoding của khuôn mặt đầu tiên
                    face_encoding = face_recognition.face_encodings(image, face_locations)[0]
                    user_encodings.append(face_encoding)
            except Exception as e:
                print(f"Lỗi khi xử lý {img_path}: {str(e)}")
                continue
        
        if user_encodings:
            # Lưu trung bình của các encoding
            face_encodings[username] = np.mean(user_encodings, axis=0)
    
    # Lưu mô hình
    model_path = os.path.join(data_dir, "face_model.pkl")
    with open(model_path, 'wb') as f:
        pickle.dump(face_encodings, f)
    
    print(f"Đã huấn luyện xong mô hình cho {len(face_encodings)} người dùng")
    return model_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện mô hình nhận diện khuôn mặt")
    parser.add_argument("--data-dir", default="data", help="Đường dẫn đến thư mục dữ liệu")
    args = parser.parse_args()
    
    train_face_model(args.data_dir)
