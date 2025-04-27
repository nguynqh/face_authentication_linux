#!/usr/bin/env python3
import cv2
import os
import time
import argparse

def collect_face_data(username, num_samples=40, output_dir="data"):
    # Tạo thư mục cho người dùng
    user_dir = os.path.join(output_dir, username)
    os.makedirs(user_dir, exist_ok=True)
    
    # Khởi tạo camera - sử dụng camera thứ 1 (index=1) thay vì camera mặc định (index=0)
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Không thể mở camera với index 1! Thử với index 2...")
        cap = cv2.VideoCapture(2)  # Thử với camera thứ 2 nếu camera thứ 1 không mở được
        if not cap.isOpened():
            print("Không thể mở camera nào! Hãy kiểm tra lại thiết bị camera của bạn.")
            return
    
    # Tải bộ nhận diện khuôn mặt
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    count = 0
    print(f"Thu thập dữ liệu khuôn mặt cho {username}. Nhấn 's' để bắt đầu...")
    
    waiting_for_start = True
    while waiting_for_start:
        ret, frame = cap.read()
        if not ret:
            print("Không thể đọc khung hình!")
            break
        
        cv2.imshow("Collect Face Data", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            waiting_for_start = False
        elif key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            return
    
    print("Bắt đầu thu thập dữ liệu...")
    
    while count < num_samples:
        ret, frame = cap.read()
        if not ret:
            print("Không thể đọc khung hình!")
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Chỉ lưu hình ảnh khuôn mặt khi đã phát hiện
            face_img = frame[y:y+h, x:x+w]
            img_path = os.path.join(user_dir, f"{username}_{count}.jpg")
            cv2.imwrite(img_path, face_img)
            count += 1
            print(f"Đã thu thập {count}/{num_samples} hình ảnh")
            time.sleep(0.5)  # Nghỉ giữa các lần chụp
            
        cv2.imshow("Collect Face Data", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    print(f"Đã thu thập đủ {count} hình ảnh khuôn mặt cho {username}")
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thu thập dữ liệu khuôn mặt")
    parser.add_argument("--username", required=True, help="Tên người dùng")
    parser.add_argument("--samples", type=int, default=20, help="Số lượng mẫu cần thu thập")
    args = parser.parse_args()
    
    collect_face_data(args.username, args.samples)
