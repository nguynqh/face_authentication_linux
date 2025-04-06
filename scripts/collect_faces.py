#!/usr/bin/env python3
import cv2
import os
import time
import argparse
import numpy as np

def register_face(username, num_samples=40, output_dir="data"):
    # Tạo thư mục cho người dùng
    user_dir = os.path.join(output_dir, username)
    os.makedirs(user_dir, exist_ok=True)
    
    # Khởi tạo camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Không thể mở camera!")
        return
    
    # Tải bộ nhận diện khuôn mặt
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Lấy kích thước khung hình
    ret, frame = cap.read()
    if not ret:
        print("Không thể đọc khung hình!")
        return
    
    height, width = frame.shape[:2]
    
    # Cấu hình giao diện
    window_name = "Đăng Ký Khuôn Mặt"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    # Tạo hướng dẫn oval (hình bầu dục)
    oval_size = min(width, height) // 2
    oval_center = (width // 2, height // 2)
    oval_axes = (oval_size, int(oval_size * 1.3))  # Tỷ lệ bầu dục phù hợp với khuôn mặt
    
    count = 0
    status_text = "Nhấn 's' để bắt đầu đăng ký khuôn mặt"
    
    waiting_for_start = True
    start_time = time.time()
    capturing = False
    face_detected = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Không thể đọc khung hình!")
            break
        
        # Flip ảnh để tạo cảm giác mirror như trên điện thoại
        frame = cv2.flip(frame, 1)
        
        # Tạo một bản sao để vẽ UI
        display_frame = frame.copy()
        
        # Vẽ nền mờ cho UI
        overlay = display_frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, height), (0, 0, 0), -1)
        
        # Vẽ hướng dẫn oval
        cv2.ellipse(overlay, oval_center, oval_axes, 0, 0, 360, (255, 255, 255), 2)
        
        # Tạo mask hình oval
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.ellipse(mask, oval_center, oval_axes, 0, 0, 360, 255, -1)
        
        # Áp dụng mask vào hình
        masked_area = cv2.bitwise_and(frame, frame, mask=mask)
        
        # Blend overlay với frame
        alpha = 0.3  # Độ mờ
        cv2.addWeighted(overlay, alpha, display_frame, 1 - alpha, 0, display_frame)
        
        # Hiển thị phần mặt trong oval
        display_frame = cv2.bitwise_and(display_frame, display_frame, mask=~mask)
        display_frame = cv2.add(display_frame, masked_area)
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        face_detected = False
        largest_face = None
        largest_area = 0
        
        # Tìm khuôn mặt lớn nhất
        for (x, y, w, h) in faces:
            if w * h > largest_area:
                largest_area = w * h
                largest_face = (x, y, w, h)
        
        # Xử lý khuôn mặt lớn nhất
        if largest_face is not None:
            x, y, w, h = largest_face
            face_center = (x + w // 2, y + h // 2)
            
            # Kiểm tra xem khuôn mặt có nằm gần trung tâm oval không
            distance = np.sqrt((face_center[0] - oval_center[0])**2 + (face_center[1] - oval_center[1])**2)
            
            if distance < oval_size * 0.2 and w > oval_size * 0.5 and w < oval_size * 1.2:
                face_detected = True
                # Vẽ khung xanh lá khi khuôn mặt đúng vị trí
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            else:
                # Vẽ khung đỏ khi khuôn mặt chưa đúng vị trí
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
        
        # Hiển thị thanh tiến trình
        if not waiting_for_start and capturing:
            progress = int((width * count) / num_samples)
            cv2.rectangle(display_frame, (0, height - 30), (progress, height), (0, 255, 0), -1)
            cv2.rectangle(display_frame, (0, height - 30), (width, height), (255, 255, 255), 2)
            
            # Hiển thị số lượng ảnh đã chụp
            status_text = f"Đang đăng ký: {count}/{num_samples} khung hình"
            
            # Tự động chụp khi mặt được phát hiện đúng vị trí
            current_time = time.time()
            if face_detected and current_time - start_time > 0.3:  # Chụp mỗi 0.3 giây
                # Lưu hình ảnh khuôn mặt
                face_img = frame[y:y+h, x:x+w]
                img_path = os.path.join(user_dir, f"{username}_{count}.jpg")
                cv2.imwrite(img_path, face_img)
                count += 1
                start_time = current_time
                
                # Hiệu ứng flash nhẹ khi chụp
                flash = display_frame.copy()
                cv2.rectangle(flash, (0, 0), (width, height), (255, 255, 255), -1)
                cv2.addWeighted(flash, 0.3, display_frame, 0.7, 0, display_frame)
        
        # Hiển thị hướng dẫn
        if waiting_for_start:
            status_text = "Nhấn 's' để bắt đầu đăng ký khuôn mặt"
        elif face_detected:
            if not capturing:
                status_text = "Khuôn mặt đã sẵn sàng. Giữ nguyên vị trí."
        else:
            status_text = "Đặt khuôn mặt vào giữa hình oval"
        
        # Thêm text hướng dẫn
        cv2.rectangle(display_frame, (0, height - 80), (width, height - 30), (0, 0, 0), -1)
        cv2.putText(display_frame, status_text, (20, height - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Hiển thị giao diện
        cv2.imshow(window_name, display_frame)
        
        # Xử lý phím bấm
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s') and waiting_for_start:
            waiting_for_start = False
            capturing = True
            print("Bắt đầu đăng ký khuôn mặt...")
        elif key == ord('q') or count >= num_samples:
            break
    
    if count >= num_samples:
        print(f"Đăng ký khuôn mặt thành công với {count} hình ảnh cho {username}")
    else:
        print(f"Đăng ký khuôn mặt đã dừng tại {count}/{num_samples} hình ảnh")
        
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Đăng ký khuôn mặt người dùng")
    parser.add_argument("--username", required=True, help="Tên người dùng")
    parser.add_argument("--samples", type=int, default=20, help="Số lượng mẫu cần thu thập")
    args = parser.parse_args()
    
    register_face(args.username, args.samples)
