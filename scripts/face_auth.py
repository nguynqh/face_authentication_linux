#!/usr/bin/env python3
import cv2
import pickle
import face_recognition
import numpy as np
import argparse
import os
import time
import glob
import sys
import subprocess

def configure_camera(cap):
    """Cấu hình thêm các tham số cho camera để hoạt động mượt hơn"""
    # Thiết lập độ phân giải thấp hơn để xử lý nhanh hơn
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    # Giảm FPS để giảm tải xử lý
    cap.set(cv2.CAP_PROP_FPS, 15)
    # Tắt chế độ tự động lấy nét để tốc độ nhanh hơn (tùy thuộc vào camera)
    try:
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    except:
        pass
    # Tắt chế độ tự động phơi sáng (nếu được hỗ trợ)
    try:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
    except:
        pass
    return cap

def detect_camera_devices():
    """Phát hiện các thiết bị camera có sẵn trên hệ thống"""
    video_devices = []
    
    # Phương pháp 1: Kiểm tra /dev/videoX
    try:
        video_devices = sorted(glob.glob('/dev/video*'))
        if video_devices:
            print(f"Phát hiện thiết bị camera: {video_devices}")
    except Exception as e:
        print(f"Không thể kiểm tra thiết bị camera: {e}")
    
    # Phương pháp 2: Sử dụng v4l2-ctl nếu có sẵn
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, timeout=2)
        if result.returncode == 0:
            print("Thông tin thiết bị camera từ v4l2-ctl:")
            print(result.stdout)
    except:
        pass
        
    return video_devices

def open_camera_with_backend(camera_idx, headless=False):
    """Mở camera với nhiều backend và phương pháp khác nhau cho đến khi thành công"""
    print(f"Đang thử mở camera {camera_idx}...")
    
    # Thử với đường dẫn trực tiếp nếu camera_idx là số nguyên
    if isinstance(camera_idx, int):
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
    
    # Danh sách các backend ưu tiên
    backends = []
    
    # Thêm backend V4L2 nếu có sẵn (phổ biến trên Linux)
    if hasattr(cv2, 'CAP_V4L2'):
        backends.append((cv2.CAP_V4L2, "V4L2"))
    
    # Thêm backend khác nếu cần
    if hasattr(cv2, 'CAP_V4L'):
        backends.append((cv2.CAP_V4L, "V4L"))
    
    # Thêm backend gstreamer nếu headless
    if headless and hasattr(cv2, 'CAP_GSTREAMER'):
        backends.append((cv2.CAP_GSTREAMER, "GStreamer"))
        
    # Thêm backend mặc định vào cuối
    backends.append((None, "Default"))
    
    # Thử từng backend cho đến khi thành công
    for backend, name in backends:
        try:
            print(f"Thử mở camera {camera_idx} với backend {name}...")
            
            if backend is not None:
                # Thử với một số tùy chọn khác nhau
                for api_preference in [backend, backend | cv2.CAP_ANY]:
                    try:
                        print(f"  Thử với API preference: {api_preference}")
                        cap = cv2.VideoCapture(camera_idx, api_preference)
                        if cap.isOpened():
                            # Đọc frame thử để xác nhận camera hoạt động
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                print(f"  Đã mở camera {camera_idx} thành công với backend {name}!")
                                return cap
                            else:
                                print("  Camera mở được nhưng không đọc được frame")
                                cap.release()
                    except Exception as e:
                        print(f"  Lỗi khi thử API preference: {e}")
            else:
                # Thử cách mặc định
                cap = cv2.VideoCapture(camera_idx)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print(f"Đã mở camera {camera_idx} thành công với backend mặc định")
                        return cap
                    else:
                        print("Camera mở được nhưng không đọc được frame")
                        cap.release()
        except Exception as e:
            print(f"Lỗi khi mở camera {camera_idx} với backend {name}: {e}")
    
    # Thử với GStreamer pipeline cho headless mode
    if headless and hasattr(cv2, 'CAP_GSTREAMER'):
        try:
            print("Thử mở camera với GStreamer pipeline...")
            pipeline = f"v4l2src device=/dev/video{camera_idx} ! videoconvert ! appsink"
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print("Đã mở camera thành công với GStreamer pipeline")
                    return cap
                else:
                    print("Camera mở được bằng GStreamer nhưng không đọc được frame")
                    cap.release()
        except Exception as e:
            print(f"Lỗi khi thử GStreamer: {e}")
            
    # Các phương pháp mở rộng mới - thử dùng ffmpeg một cách rõ ràng
    try:
        print(f"Thử mở camera {camera_idx} với backend FFMPEG...")
        if hasattr(cv2, 'CAP_FFMPEG'):
            cap = cv2.VideoCapture(camera_idx, cv2.CAP_FFMPEG)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print("Đã mở camera thành công với backend FFMPEG")
                    return cap
                else:
                    print("Camera mở được bằng FFMPEG nhưng không đọc được frame")
                    cap.release()
    except Exception as e:
        print(f"Lỗi khi thử FFMPEG: {e}")
        
    # Thử tiếp cận từ chuỗi URL trực tiếp
    try:
        print(f"Thử mở camera {camera_idx} với URL v4l2...")
        cap = cv2.VideoCapture(f"v4l2:/dev/video{camera_idx}")
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print("Đã mở camera thành công với URL v4l2")
                return cap
            else:
                print("Camera mở được bằng URL v4l2 nhưng không đọc được frame")
                cap.release()
    except Exception as e:
        print(f"Lỗi khi thử URL v4l2: {e}")
        
    # Thử tiếp cận không thông qua OpenCV (sử dụng v4l2py nếu được cài đặt)
    try:
        import importlib
        v4l2 = importlib.util.find_spec('v4l2py')
        if v4l2:
            print("Thử mở camera với v4l2py...")
            import v4l2py.device
            device = v4l2py.device.Device(f"/dev/video{camera_idx}")
            print(f"Thiết bị camera mở được: {device}")
            # Chuyển từ v4l2py device sang OpenCV
            cap = cv2.VideoCapture(camera_idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print("Đã mở camera thành công với v4l2py + OpenCV")
                    device.close()  # Đóng v4l2py device
                    return cap
            device.close()
    except Exception as e:
        print(f"Lỗi khi thử v4l2py: {e}")
    
    # Thử dùng subprocess để kiểm tra trạng thái camera
    try:
        subprocess.run(['v4l2-ctl', '-d', f'/dev/video{camera_idx}', '--all'],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1)
        print(f"Thiết bị camera /dev/video{camera_idx} có vẻ hoạt động với v4l2-ctl")
        # Thử lại OpenCV sau khi kiểm tra bằng v4l2-ctl
        cap = cv2.VideoCapture(camera_idx)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print("Đã mở camera thành công sau khi kiểm tra với v4l2-ctl")
                return cap
    except Exception as e:
        print(f"Lỗi khi thử v4l2-ctl: {e}")
    
    return None

def authenticate_face(username, model_path="models/face_auth_model.pkl", confidence_threshold=0.6, headless=False):
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
    
    # Xác định nếu môi trường không có GUI (không có DISPLAY hoặc trong PAM)
    gui_available = (os.environ.get('DISPLAY') and not headless and 
                     not os.environ.get('PAM_SERVICE') and
                     not os.environ.get('PAM_PYTHON_AUTHENTICATE'))
    
    # Ghi log thông tin môi trường
    log_file = "/tmp/face_auth_debug.log"
    with open(log_file, "a") as log:
        log.write(f"FACE AUTH DEBUG - Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Username: {username}\n")
        log.write(f"GUI available: {gui_available}\n")
        log.write(f"Headless mode: {headless}\n")
        log.write(f"Current UID: {os.getuid()}, EUID: {os.geteuid()}\n")
        
        # Ghi log các biến môi trường liên quan đến màn hình
        display_vars = {}
        for var in os.environ:
            if any(keyword in var.upper() for keyword in ['DISPLAY', 'X11', 'WAYLAND', 'XDG']):
                display_vars[var] = os.environ[var]
        log.write(f"Display environment variables: {display_vars}\n")
        
        # Liệt kê các thiết bị camera
        try:
            video_devices = detect_camera_devices()
            log.write(f"Video devices found: {video_devices}\n")
            
            # Kiểm tra quyền truy cập
            for dev in video_devices:
                try:
                    st = os.stat(dev)
                    perms = oct(st.st_mode)[-3:]
                    readable = os.access(dev, os.R_OK)
                    writable = os.access(dev, os.W_OK)
                    log.write(f"Permissions for {dev}: {perms} (R:{readable}, W:{writable})\n")
                except Exception as perm_err:
                    log.write(f"Error checking permissions for {dev}: {perm_err}\n")
        except Exception as dev_err:
            log.write(f"Error listing video devices: {dev_err}\n")
    
    # Thử kết nối nhiều camera khác nhau
    camera_indices = [0, 1, 2]  # Thứ tự ưu tiên thử kết nối camera
    cap = None

    # Trong môi trường không có GUI, thử truy cập camera trực tiếp từ thiết bị
    if not gui_available:
        video_devices = detect_camera_devices()
        for device in video_devices:
            try:
                device_idx = int(device.split('video')[1])
                print(f"Đang thử kết nối với thiết bị {device} (index {device_idx})...")
                cap = open_camera_with_backend(device_idx, headless=True)
                if cap is not None and cap.isOpened():
                    with open(log_file, "a") as log:
                        log.write(f"Successfully opened device {device}\n")
                    break
            except Exception as e:
                print(f"Lỗi khi thử thiết bị {device}: {e}")
    
    # Nếu chưa mở được camera, thử với các chỉ số camera
    if cap is None or not cap.isOpened():
        # Thử lần lượt các camera
        for cam_index in camera_indices:
            print(f"Đang thử kết nối camera index {cam_index}...")
            cap = open_camera_with_backend(cam_index, headless=headless)
            
            if cap is not None and cap.isOpened():
                print(f"Đã kết nối thành công với camera {cam_index}")
                with open(log_file, "a") as log:
                    log.write(f"Successfully opened camera index {cam_index}\n")
                # Cấu hình camera để tối ưu hiệu suất
                cap = configure_camera(cap)
                break
    
    if cap is None or not cap.isOpened():
        with open(log_file, "a") as log:
            log.write("Failed to open any camera\n")
        print("FAILURE: Không thể mở camera nào!")
        return False
    
    # Khởi động camera - thử một số frame đầu để ổn định
    print("Đang khởi động camera...")
    warm_up_frames = []
    for i in range(5):
        ret, frame = cap.read()
        if ret and frame is not None:
            warm_up_frames.append(frame)
        time.sleep(0.1)
    
    if not warm_up_frames:
        with open(log_file, "a") as log:
            log.write("Camera opened but can't read frames during warm up\n")
        print("FAILURE: Camera không trả về hình ảnh trong quá trình khởi động")
        cap.release()
        return False
    
    # Lưu một khung hình test để debug
    try:
        test_file = "/tmp/face_auth_test_frame.jpg"
        cv2.imwrite(test_file, warm_up_frames[-1])  # Lưu frame cuối cùng
        with open(log_file, "a") as log:
            log.write(f"Test frame saved to {test_file}\n")
    except Exception as e:
        with open(log_file, "a") as log:
            log.write(f"Failed to save test frame: {e}\n")
    
    # Lấy nhiều khung hình để xác thực, với timeout
    max_attempts = 10  # Tăng số lần thử
    successful_attempts = 0
    face_detected = False
    timeout_start = time.time()
    timeout_seconds = 7  # Timeout sau 7 giây
    
    print("Đang đợi khuôn mặt...")
    while time.time() - timeout_start < timeout_seconds and successful_attempts < 3:
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"FAILURE: Không thể đọc khung hình")
            continue
            
        # Giảm kích thước frame để xử lý nhanh hơn
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        
        # Tìm khuôn mặt và mã hóa
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")  # Sử dụng mô hình HOG nhanh hơn
        
        if len(face_locations) == 0:
            # Hiển thị khung hình với chỉ dẫn nếu đang chạy trong môi trường có GUI
            if gui_available:
                # Resize frame for display
                display_scale = 2.0 # Tăng kích thước giao diện từ 1.5 lên 2.0
                display_width = int(frame.shape[1] * display_scale)
                display_height = int(frame.shape[0] * display_scale)
                display_frame = cv2.resize(frame, (display_width, display_height))

                if not face_detected:
                    cv2.putText(display_frame, "Khong phat hien khuon mat", (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    # Draw rectangles on the resized frame (adjust coordinates)
                    for (top, right, bottom, left) in face_locations:
                        # Scale coordinates according to the display_scale and the original resize factor (0.5)
                        display_top = int(top * 2 * display_scale)
                        display_right = int(right * 2 * display_scale)
                        display_bottom = int(bottom * 2 * display_scale)
                        display_left = int(left * 2 * display_scale)
                        cv2.rectangle(display_frame, (display_left, display_top), (display_right, display_bottom), (0, 255, 0), 2)

                cv2.imshow("Face Authentication", display_frame)
                cv2.waitKey(1)
            continue
        
        face_detected = True
        # Hiển thị khung hình với viền khuôn mặt nếu đang chạy trong môi trường có GUI
        if gui_available:
            for (top, right, bottom, left) in face_locations:
                # Vẽ viền khuôn mặt (nhân đôi tọa độ vì đã thu nhỏ hình)
                cv2.rectangle(display_frame, (left*2, top*2), (right*2, bottom*2), (0, 255, 0), 2)
            cv2.imshow("Face Authentication", display_frame)
            cv2.waitKey(1)
        
        # Lưu frame có khuôn mặt để debug (use original frame)
        if face_detected and successful_attempts == 0:
            try:
                face_file = "/tmp/face_auth_detected_face.jpg"
                cv2.imwrite(face_file, frame) # Save original frame
                with open(log_file, "a") as log:
                    log.write(f"Face frame saved to {face_file}\n")
            except Exception as e:
                with open(log_file, "a") as log:
                    log.write(f"Failed to save face frame: {e}\n")
        
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
                with open(log_file, "a") as log:
                    log.write(f"Prediction: user={predicted_user}, confidence={confidence:.2f}\n")
                
                # Kiểm tra xem người dùng dự đoán có khớp với người dùng đăng nhập không
                if predicted_user == username and confidence >= confidence_threshold:
                    successful_attempts += 1
                    print(f"Xác thực thành công lần {successful_attempts}/3")
                    with open(log_file, "a") as log:
                        log.write(f"Successful authentication attempt {successful_attempts}/3\n")
        
        # Nghỉ ngắn giữa các lần thử để giảm tải CPU
        time.sleep(0.1)
    
    # Đóng camera và cửa sổ hiển thị
    cap.release()
    if gui_available:
        cv2.destroyAllWindows()
    
    # Xác thực thành công nếu:
    # 1. Có phát hiện khuôn mặt
    # 2. Có ít nhất 3 lần thử thành công
    if not face_detected:
        with open(log_file, "a") as log:
            log.write("Authentication failed: No face detected\n")
        print("FAILURE: Không phát hiện khuôn mặt trong thời gian chờ")
        return False
        
    if successful_attempts >= 3:
        with open(log_file, "a") as log:
            log.write("Authentication successful\n")
        print("SUCCESS")
        return True
    else:
        with open(log_file, "a") as log:
            log.write(f"Authentication failed: Only {successful_attempts}/3 successful attempts\n")
        print(f"FAILURE: Chỉ xác thực thành công {successful_attempts}/3 lần yêu cầu")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Xác thực khuôn mặt")
    parser.add_argument("--username", required=True, help="Tên người dùng để xác thực")
    parser.add_argument("--model", default="models/face_auth_model.pkl", help="Đường dẫn đến file model")
    parser.add_argument("--threshold", type=float, default=0.6, help="Ngưỡng độ tin cậy")
    parser.add_argument("--headless", action="store_true", help="Chạy không cần giao diện đồ họa")
    args = parser.parse_args()
    
    # Kiểm tra biến môi trường để xác định chế độ headless
    headless_mode = args.headless or os.environ.get('NO_X_SERVER') == '1' or not os.environ.get('DISPLAY')
    
    # Nếu đang chạy trong PAM, tự động kích hoạt chế độ headless
    if os.environ.get('PAM_SERVICE') or os.environ.get('PAM_PYTHON_AUTHENTICATE'):
        headless_mode = True
    
    if headless_mode:
        print("Chạy trong chế độ không cần giao diện đồ họa (headless)")
    
    authenticate_face(args.username, args.model, args.threshold, headless=headless_mode)
