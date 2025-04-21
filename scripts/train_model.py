#!/usr/bin/env python3
import os
import pickle
import face_recognition
import numpy as np
from sklearn import svm
import argparse

def train_face_model(data_dir="data", model_output="models/face_auth_model.pkl"):
    # Kiểm tra thư mục dữ liệu
    if not os.path.exists(data_dir):
        print(f"Thư mục {data_dir} không tồn tại!")
        return
    
    # Kiểm tra thư mục đầu ra
    model_dir = os.path.dirname(model_output)
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    
    # Chuẩn bị dữ liệu
    face_encodings = []
    face_names = []
    
    # Duyệt qua các thư mục người dùng
    for user_dir in os.listdir(data_dir):
        user_path = os.path.join(data_dir, user_dir)
        if os.path.isdir(user_path):
            print(f"Đang xử lý dữ liệu cho người dùng: {user_dir}")
            
            # Duyệt qua các file ảnh trong thư mục người dùng
            for img_file in os.listdir(user_path):
                if img_file.endswith(".jpg") or img_file.endswith(".png"):
                    img_path = os.path.join(user_path, img_file)
                    
                    # Đọc ảnh và tạo mã hóa khuôn mặt
                    try:
                        image = face_recognition.load_image_file(img_path)
                        encodings = face_recognition.face_encodings(image)
                        
                        if len(encodings) > 0:
                            face_encodings.append(encodings[0])
                            face_names.append(user_dir)
                        else:
                            print(f"Không tìm thấy khuôn mặt trong ảnh: {img_path}")
                    except Exception as e:
                        print(f"Lỗi khi xử lý ảnh {img_path}: {e}")
    
    if len(face_encodings) == 0:
        print("Không có dữ liệu khuôn mặt nào được tìm thấy!")
        return
    
    # Huấn luyện mô hình SVM
    print("Đang huấn luyện mô hình...")
    clf = svm.SVC(gamma='scale', probability=True)
    clf.fit(face_encodings, face_names)
    
    # Lưu mô hình
    with open(model_output, 'wb') as f:
        pickle.dump((clf, face_encodings, face_names), f)
    
    print(f"Đã lưu mô hình vào {model_output}")
    print(f"Số lượng người dùng: {len(set(face_names))}")
    print(f"Tổng số mẫu khuôn mặt: {len(face_encodings)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Huấn luyện mô hình nhận diện khuôn mặt")
    parser.add_argument("--data-dir", default="data", help="Đường dẫn đến thư mục dữ liệu")
    parser.add_argument("--output", default="models/face_auth_model.pkl", help="Đường dẫn lưu mô hình")
    args = parser.parse_args()
    
    train_face_model(args.data_dir, args.output)
