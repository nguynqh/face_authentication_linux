#!/usr/bin/env python3
import cv2
import pickle
import face_recognition
import numpy as np
import argparse
import os
import time

def configure_camera(cap):
    """Cấu hình thêm các tham số cho camera để hoạt động mượt hơn"""
    # Thiết lập độ phân giải thấp hơn để xử lý nhanh hơn
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    # Giảm FPS để giảm tải xử lý
    cap.set(cv2.CAP_PROP_FPS, 15)
    # Tắt chế độ tự động lấy nét để tốc độ nhanh hơn (tùy thuộc vào camera)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    # Tắt chế độ tự động phơi sáng (nếu được hỗ trợ)
    try:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
    except:
        pass
    return cap

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
    
    # Thử kết nối nhiều camera khác nhau
    camera_indices = [1, 2, 0]  # Thứ tự ưu tiên thử kết nối camera
    cap = None
    
    # Thử lần lượt các camera
    for cam_index in camera_indices:
        print(f"Đang thử kết nối camera {cam_index}...")
        cap = cv2.VideoCapture(cam_index)
        
        if cap.isOpened():
            print(f"Đã kết nối thành công với camera {cam_index}")
            # Cấu hình camera để tối ưu hiệu suất
            cap = configure_camera(cap)
            break
    
    if cap is None or not cap.isOpened():
        print("FAILURE: Không thể mở camera nào!")
        return False
    
    # Khởi động camera - thử một số frame đầu để ổn định
    print("Đang khởi động camera...")
    for i in range(5):
        ret, _ = cap.read()
        time.sleep(0.1)
    
    # Kiểm tra xem camera có thực sự hoạt động không
    ret, test_frame = cap.read()
    if not ret or test_frame is None:
        print("FAILURE: Camera không trả về hình ảnh")
        cap.release()
        return False
        
    # Lấy nhiều khung hình để xác thực, với timeout
    max_attempts = 10  # Tăng số lần thử
    successful_attempts = 0
    face_detected = False
    timeout_start = time.time()
    timeout_seconds = 7  # Timeout sau 7 giây
    
    print("Đang đợi khuôn mặt...")
    while time.time() - timeout_start < timeout_seconds and successful_attempts < 3:
        ret, frame = cap.read()
        if not ret:
            print(f"FAILURE: Không thể đọc khung hình")
            continue
            
        # Giảm kích thước frame để xử lý nhanh hơn
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        
        # Tìm khuôn mặt và mã hóa
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")  # Sử dụng mô hình HOG nhanh hơn
        
        if len(face_locations) == 0:
            # Hiển thị khung hình với chỉ dẫn nếu đang chạy trong môi trường có GUI
            if os.environ.get('DISPLAY'):
                cv2.putText(frame, "Không phát hiện khuôn mặt", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow("Face Authentication", frame)
                cv2.waitKey(1)
            continue
        
        face_detected = True
        # Hiển thị khung hình với viền khuôn mặt nếu đang chạy trong môi trường có GUI
        if os.environ.get('DISPLAY'):
            for (top, right, bottom, left) in face_locations:
                # Vẽ viền khuôn mặt (nhân đôi tọa độ vì đã thu nhỏ hình)
                cv2.rectangle(frame, (left*2, top*2), (right*2, bottom*2), (0, 255, 0), 2)
            cv2.imshow("Face Authentication", frame)
            cv2.waitKey(1)
        
        # Chỉ xử lý khuôn mặt đầu tiên phát hiện để tăng tốc
        if len(face_locations) > 0:
            face_encodings = face_recognition.face_encodings(rgb_frame, [face_locations[0]])
            
            if len(face_encodings) > 0:
                # Dự đoán người dùng và độ tin cậy
                predictions = clf.predict_proba([face_encodings[0]])[0]
                best_match_index = np.argmax(predictions)
                confidence = predictions[best_match_index]
                predicted_user = clf.classes_[best_match_index]
                
                print(f"Dự đoán người dùng: {predicted_user}, Độ tin cậy: {confidence:.2f}")
                
                # Kiểm tra xem người dùng dự đoán có khớp với người dùng đăng nhập không
                if predicted_user == username and confidence >= confidence_threshold:
                    successful_attempts += 1
                    print(f"Xác thực thành công lần {successful_attempts}/3")
        
        # Nghỉ ngắn giữa các lần thử để giảm tải CPU
        time.sleep(0.1)
    
    # Đóng camera và cửa sổ hiển thị
    cap.release()
    if os.environ.get('DISPLAY'):
        cv2.destroyAllWindows()
    
    # Xác thực thành công nếu:
    # 1. Có phát hiện khuôn mặt
    # 2. Có ít nhất 3 lần thử thành công
    if not face_detected:
        print("FAILURE: Không phát hiện khuôn mặt trong thời gian chờ")
        return False
        
    if successful_attempts >= 3:
        print("SUCCESS")
        return True
    else:
        print(f"FAILURE: Chỉ xác thực thành công {successful_attempts}/3 lần yêu cầu")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Xác thực khuôn mặt")
    parser.add_argument("--username", required=True, help="Tên người dùng để xác thực")
    parser.add_argument("--model", default="models/face_auth_model.pkl", help="Đường dẫn đến file model")
    parser.add_argument("--threshold", type=float, default=0.6, help="Ngưỡng độ tin cậy")
    args = parser.parse_args()
    
    authenticate_face(args.username, args.model, args.threshold)
