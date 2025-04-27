#!/usr/bin/env python3
import cv2
import os
import time
import argparse
import gc
import numpy as np
import threading
import signal
import sys

def signal_handler(sig, frame):
    print('Đã nhận tín hiệu ngắt. Đang thoát...')
    cv2.destroyAllWindows()
    sys.exit(0)

# Đăng ký xử lý tín hiệu Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

def configure_camera(cap, skip_config=False):
    """Cấu hình camera với các tùy chọn an toàn hơn"""
    if skip_config:
        print("Bỏ qua cấu hình camera chi tiết")
        return cap
        
    print("Đang áp dụng cấu hình camera cơ bản...")
    # Chỉ thiết lập độ phân giải và FPS, không thiết lập định dạng
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 15)
        print("Đã áp dụng cấu hình độ phân giải và FPS")
    except Exception as e:
        print(f"Cảnh báo: Không thể thiết lập độ phân giải/FPS: {e}")
    
    return cap

def open_camera_with_backend(camera_idx):
    """Mở camera với nhiều backend khác nhau cho đến khi thành công"""
    # Danh sách các backend ưu tiên
    backends = []
    
    # Thêm backend V4L2 nếu có sẵn (phổ biến trên Linux)
    if hasattr(cv2, 'CAP_V4L2'):
        backends.append((cv2.CAP_V4L2, "V4L2"))
    
    # Thêm backend khác nếu cần
    if hasattr(cv2, 'CAP_V4L'):
        backends.append((cv2.CAP_V4L, "V4L"))
        
    # Thêm backend mặc định vào cuối
    backends.append((None, "Default"))
    
    # Thử từng backend cho đến khi thành công
    for backend, name in backends:
        try:
            print(f"Thử mở camera {camera_idx} với backend {name}...")
            
            if backend is not None:
                # Thử với một số tùy chọn khác nhau
                for api_preference in [backend, backend | cv2.CAP_ANY, backend | cv2.CAP_DSHOW]:
                    try:
                        print(f"  Thử với API preference: {api_preference}")
                        cap = cv2.VideoCapture(camera_idx, api_preference)
                        if cap.isOpened():
                            print(f"  Đã mở camera {camera_idx} thành công!")
                            return cap
                    except Exception as e:
                        print(f"  Lỗi khi thử API preference: {e}")
            else:
                # Thử cách mặc định
                cap = cv2.VideoCapture(camera_idx)
                if cap.isOpened():
                    print(f"Đã mở camera {camera_idx} thành công với backend mặc định")
                    return cap
                
                # Thử với index dạng chuỗi "/dev/videoX"
                try:
                    dev_path = f"/dev/video{camera_idx}"
                    if os.path.exists(dev_path):
                        print(f"Thử mở camera qua đường dẫn: {dev_path}")
                        cap = cv2.VideoCapture(dev_path)
                        if cap.isOpened():
                            print(f"Đã mở camera {dev_path} thành công")
                            return cap
                except Exception as e:
                    print(f"Lỗi khi thử mở {dev_path}: {e}")
        except Exception as e:
            print(f"Lỗi khi mở camera {camera_idx} với backend {name}: {e}")
    
    return None

def test_camera_connection(verbose=False):
    """Kiểm tra và tìm camera có thể sử dụng với thông tin chi tiết hơn"""
    camera_indices = [0, 1, 2, 3]
    working_cameras = []
    
    print("Đang kiểm tra các camera có sẵn...")
    for idx in camera_indices:
        try:
            print(f"Thử kết nối camera {idx}...")
            cap = open_camera_with_backend(idx)
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    if verbose:
                        print(f"- Camera {idx}: OK")
                        print(f"  + Kích thước frame: {frame.shape[1]}x{frame.shape[0]}")
                        print(f"  + FPS hiện tại: {cap.get(cv2.CAP_PROP_FPS)}")
                    else:
                        print(f"Camera {idx} hoạt động tốt")
                    working_cameras.append(idx)
                else:
                    print(f"Camera {idx} mở được nhưng không đọc được frame")
                cap.release()
            else:
                print(f"Không thể mở camera {idx}")
        except Exception as e:
            print(f"Lỗi khi kiểm tra camera {idx}: {e}")
    
    if not working_cameras:
        print("\nKhông tìm thấy camera nào hoạt động!")
        print("Gợi ý khắc phục:")
        print("1. Kiểm tra kết nối camera")
        print("2. Đảm bảo không có ứng dụng nào khác đang sử dụng camera")
        print("3. Thử chạy 'sudo modprobe uvcvideo' để tải lại driver camera")
    else:
        print(f"\nTìm thấy {len(working_cameras)} camera hoạt động: {working_cameras}")
    
    return working_cameras

def collect_face_data(username, num_samples=40, output_dir="data", camera_idx=None):
    # Tạo thư mục cho người dùng
    user_dir = os.path.join(output_dir, username)
    os.makedirs(user_dir, exist_ok=True)
    
    # Kiểm tra các camera nếu chưa chỉ định
    if camera_idx is None:
        working_cameras = test_camera_connection()
        if not working_cameras:
            print("Không tìm thấy camera nào hoạt động! Hãy kiểm tra kết nối camera.")
            return
        camera_idx = working_cameras[0]
    
    # Mở camera với các backend khác nhau cho đến khi thành công
    cap = open_camera_with_backend(camera_idx)
    
    if cap is None or not cap.isOpened():
        print(f"Không thể mở camera {camera_idx}! Hãy thử chỉ số khác.")
        return
    
    # Cấu hình camera để tối ưu hiệu suất
    cap = configure_camera(cap)
    
    # Khởi động camera - đọc một số frame để ổn định
    print("Đang khởi động camera...")
    for _ in range(5):
        cap.read()
        time.sleep(0.1)
    
    # Tải bộ nhận diện khuôn mặt với cấu hình nhẹ
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml')
    
    # Frame queue và biến điều khiển luồng cho camera reader
    frame_queue = []
    stop_thread = False
    
    def camera_reader():
        """Luồng riêng để đọc frame từ camera"""
        try:
            while not stop_thread:
                ret, frame = cap.read()
                if ret:
                    # Giới hạn kích thước queue để tránh rò rỉ bộ nhớ
                    if len(frame_queue) > 2:
                        frame_queue.pop(0)
                    frame_queue.append(frame)
                time.sleep(0.01)  # Giảm tốc độ đọc để giảm tải CPU
        except Exception as e:
            print(f"Lỗi trong camera_reader: {e}")
    
    # Bắt đầu luồng đọc camera
    reader_thread = threading.Thread(target=camera_reader)
    reader_thread.daemon = True
    reader_thread.start()
    
    try:
        count = 0
        print(f"Thu thập dữ liệu khuôn mặt cho {username}. Nhấn 's' để bắt đầu...")
        
        waiting_for_start = True
        while waiting_for_start and not stop_thread:
            if len(frame_queue) > 0:
                # Lấy frame mới nhất
                frame = frame_queue[-1].copy()
                
                # Hiển thị hướng dẫn
                cv2.putText(frame, "Nhan 's' de bat dau, 'q' de thoat", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("Thu thap Du lieu Khuon mat", frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('s'):
                    waiting_for_start = False
                    # Xóa queue để lấy frame mới
                    frame_queue.clear()
                elif key == ord('q'):
                    stop_thread = True
                    cv2.destroyAllWindows()
                    return
        
        print("Bắt đầu thu thập dữ liệu...")
        
        # Hiển thị các khuôn mặt đã thu thập
        faces_grid = None
        last_face_detect_time = time.time()
        face_detect_timeout = 10  # Timeout 10 giây nếu không phát hiện khuôn mặt
        
        while count < num_samples and not stop_thread:
            if len(frame_queue) > 0:
                # Lấy frame mới nhất
                frame = frame_queue[-1].copy()
                
                # Hiển thị trạng thái
                cv2.putText(frame, f"Da thu thap: {count}/{num_samples}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "Nhan 'q' de huy", (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Kiểm tra timeout nếu không phát hiện khuôn mặt
                current_time = time.time()
                if current_time - last_face_detect_time > face_detect_timeout:
                    cv2.putText(frame, "Khong phat hien khuon mat! Di chuyen vao tam nhin", 
                                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Chuyển đổi sang thang màu xám để phát hiện khuôn mặt nhanh hơn
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Phát hiện khuôn mặt với các tham số tối ưu
                # minSize để bỏ qua các khuôn mặt quá nhỏ, scaleFactor nhỏ hơn để phát hiện chính xác hơn
                faces = face_cascade.detectMultiScale(
                    gray, 
                    scaleFactor=1.1, 
                    minNeighbors=5, 
                    minSize=(30, 30),
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
                
                # Kiểm tra xem có phát hiện khuôn mặt nào không
                if len(faces) > 0:
                    last_face_detect_time = current_time
                    
                    # Lưu khuôn mặt lớn nhất được phát hiện
                    largest_face = None
                    largest_area = 0
                    
                    for (x, y, w, h) in faces:
                        area = w * h
                        if area > largest_area:
                            largest_area = area
                            largest_face = (x, y, w, h)
                    
                    if largest_face:
                        x, y, w, h = largest_face
                        # Vẽ khung xung quanh khuôn mặt
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        
                        # Chỉ lưu hình ảnh khuôn mặt khi đã phát hiện
                        face_img = frame[y:y+h, x:x+w]
                        face_img_resized = cv2.resize(face_img, (200, 200))
                        
                        # Lưu hình ảnh
                        img_path = os.path.join(user_dir, f"{username}_{count}.jpg")
                        cv2.imwrite(img_path, face_img)
                        count += 1
                        print(f"Đã thu thập {count}/{num_samples} hình ảnh")
                        
                        # Hiển thị khuôn mặt đã thu thập
                        if faces_grid is None:
                            faces_grid = face_img_resized
                        elif count % 5 == 0:  # Hiển thị mỗi 5 khuôn mặt
                            try:
                                faces_grid = np.hstack((faces_grid, face_img_resized))
                            except:
                                faces_grid = face_img_resized
                        
                        # Hiển thị khuôn mặt đã thu thập nếu có
                        if faces_grid is not None:
                            cv2.imshow("Khuon mat da thu thap", faces_grid)
                        
                        # Nghỉ giữa các lần chụp để tránh lấy nhiều ảnh giống nhau
                        time.sleep(0.3)
                
                # Hiển thị frame chính
                cv2.imshow("Thu thap Du lieu Khuon mat", frame)
                
                # Kiểm tra phím nhấn
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                
                # Gọi garbage collector mỗi 10 frame để giảm sử dụng bộ nhớ
                if count % 10 == 0:
                    gc.collect()
        
        print(f"Đã thu thập {count}/{num_samples} hình ảnh khuôn mặt cho {username}")
    
    except Exception as e:
        print(f"Lỗi khi thu thập dữ liệu: {e}")
    
    finally:
        # Dừng thread và giải phóng tài nguyên
        stop_thread = True
        reader_thread.join(timeout=1.0)
        cap.release()
        cv2.destroyAllWindows()
        gc.collect()
        
        if count > 0:
            print("Thu thập dữ liệu hoàn tất!")
        else:
            print("Không thu thập được dữ liệu. Vui lòng thử lại.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thu thập dữ liệu khuôn mặt")
    parser.add_argument("--username", required=True, help="Tên người dùng")
    parser.add_argument("--samples", type=int, default=20, help="Số lượng mẫu cần thu thập")
    parser.add_argument("--camera", type=int, help="Chỉ định camera index (nếu biết chính xác)")
    args = parser.parse_args()
    
    collect_face_data(args.username, args.samples, camera_idx=args.camera)
