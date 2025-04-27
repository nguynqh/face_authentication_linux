#!/usr/bin/env python3
import cv2
import os
import time
import sys

def test_device_files():
    """Liệt kê tất cả các file thiết bị camera"""
    print("\nDanh sách các thiết bị camera:")
    video_devices = [d for d in os.listdir("/dev") if d.startswith("video")]
    
    if not video_devices:
        print("Không tìm thấy thiết bị camera nào!")
        return []
        
    devices = []
    for device in sorted(video_devices):
        path = f"/dev/{device}"
        devices.append(path)
        print(f"- {path}")
    
    return devices

def test_camera(camera_index):
    """Kiểm tra camera cụ thể với nhiều thông tin chi tiết"""
    print(f"\n=== Kiểm tra camera {camera_index} ===")
    
    # Thử mở camera với các API khác nhau
    apis = [
        (cv2.CAP_ANY, "ANY"),
        (cv2.CAP_V4L2, "V4L2"),
        (cv2.CAP_V4L, "V4L"),
    ]
    
    for api, name in apis:
        print(f"\nĐang thử với API: {name}")
        try:
            cap = cv2.VideoCapture(camera_index, api)
            if not cap.isOpened():
                print(f"- Không mở được camera với API {name}")
                continue
                
            print(f"- Camera mở thành công với API {name}")
            
            # Hiển thị thông tin camera
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"- Độ phân giải mặc định: {width}x{height}")
            print(f"- FPS mặc định: {fps}")
            
            # Đọc một số frame
            print("- Đang đọc 5 frame thử nghiệm...")
            success_count = 0
            for i in range(5):
                ret, frame = cap.read()
                if ret:
                    success_count += 1
                    print(f"  Frame {i+1}: Thành công - Kích thước {frame.shape[1]}x{frame.shape[0]}")
                else:
                    print(f"  Frame {i+1}: Thất bại")
                time.sleep(0.1)
                
            print(f"- Đọc thành công {success_count}/5 frame")
            
            # Thử đọc frame và hiển thị
            if success_count > 0 and os.environ.get('DISPLAY'):
                print("- Hiển thị frame camera (nhấn 'q' để đóng)")
                for i in range(50):  # Hiển thị 5 giây với FPS=10
                    ret, frame = cap.read()
                    if ret:
                        cv2.putText(frame, f"Camera {camera_index} - API {name}", (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.imshow(f"Camera {camera_index} Test", frame)
                        
                        # Thoát nếu nhấn 'q'
                        if cv2.waitKey(100) & 0xFF == ord('q'):
                            break
                    else:
                        print("  Không đọc được frame")
                        break
                
                cv2.destroyAllWindows()
            
            # Đóng camera
            cap.release()
            
            # Nếu API này hoạt động tốt, không cần thử các API khác
            if success_count > 3:
                return True
                
        except Exception as e:
            print(f"- Lỗi khi thử API {name}: {str(e)}")
    
    print(f"Không API nào hoạt động tốt với camera {camera_index}")
    return False

def test_direct_device(device_path):
    """Kiểm tra trực tiếp thiết bị camera bằng đường dẫn"""
    print(f"\n=== Kiểm tra thiết bị {device_path} ===")
    
    try:
        cap = cv2.VideoCapture(device_path)
        if not cap.isOpened():
            print(f"- Không mở được thiết bị {device_path}")
            return False
            
        print(f"- Thiết bị mở thành công!")
        
        # Đọc một số frame
        print("- Đang đọc 5 frame thử nghiệm...")
        success_count = 0
        for i in range(5):
            ret, frame = cap.read()
            if ret:
                success_count += 1
                print(f"  Frame {i+1}: Thành công - Kích thước {frame.shape[1]}x{frame.shape[0]}")
            else:
                print(f"  Frame {i+1}: Thất bại")
            time.sleep(0.1)
            
        print(f"- Đọc thành công {success_count}/5 frame")
        
        # Thử hiển thị
        if success_count > 0 and os.environ.get('DISPLAY'):
            print("- Hiển thị frame camera (nhấn 'q' để đóng)")
            for i in range(50):  # Hiển thị 5 giây với FPS=10
                ret, frame = cap.read()
                if ret:
                    cv2.putText(frame, device_path, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow(f"Device Test: {device_path}", frame)
                    
                    # Thoát nếu nhấn 'q'
                    if cv2.waitKey(100) & 0xFF == ord('q'):
                        break
                else:
                    print("  Không đọc được frame")
                    break
            
            cv2.destroyAllWindows()
        
        # Đóng camera
        cap.release()
        return success_count > 3
        
    except Exception as e:
        print(f"- Lỗi khi kiểm tra thiết bị: {str(e)}")
        return False

def check_v4l2_capabilities():
    """Kiểm tra chi tiết về các thiết bị V4L2 nếu v4l2-ctl có sẵn"""
    try:
        import subprocess
        devices = test_device_files()
        
        for device in devices:
            print(f"\n=== Chi tiết thiết bị {device} ===")
            try:
                # Thử lấy thông tin thiết bị
                result = subprocess.run(['v4l2-ctl', '--device', device, '--info'], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                      text=True, timeout=3)
                
                if result.returncode == 0:
                    print(f"\nThông tin cơ bản:")
                    for line in result.stdout.split('\n'):
                        if any(keyword in line for keyword in ['Card', 'Driver', 'Bus']):
                            print(f"- {line.strip()}")
                
                # Thử lấy danh sách định dạng video được hỗ trợ
                result = subprocess.run(['v4l2-ctl', '--device', device, '--list-formats-ext'], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                      text=True, timeout=3)
                
                if result.returncode == 0:
                    print(f"\nĐịnh dạng được hỗ trợ:")
                    formats = False
                    for line in result.stdout.split('\n'):
                        if any(keyword in line for keyword in ['Format', 'Size', 'MJPG', 'YUYV', 'Interval']):
                            print(f"- {line.strip()}")
                            formats = True
                    
                    if not formats:
                        print("- Không tìm thấy định dạng video nào")
                
            except subprocess.SubprocessError:
                print(f"- Không thể kiểm tra chi tiết thiết bị {device}")
                continue
                
    except Exception as e:
        print(f"Lỗi: {e}")
        print("Cần cài đặt v4l-utils để xem chi tiết thiết bị: sudo apt install v4l-utils")

def main():
    print("===== CHƯƠNG TRÌNH KIỂM TRA CAMERA CHI TIẾT =====")
    print(f"OpenCV phiên bản: {cv2.__version__}")
    
    # Kiểm tra các thiết bị camera có sẵn
    devices = test_device_files()
    
    if not devices:
        print("\nKhông tìm thấy thiết bị camera nào! Hãy kiểm tra kết nối camera.")
        sys.exit(1)
    
    # Kiểm tra chi tiết các thiết bị V4L2
    check_v4l2_capabilities()
    
    # Kiểm tra camera bằng chỉ số
    working_cameras = []
    for i in range(4):  # Thử các chỉ số camera từ 0-3
        if test_camera(i):
            working_cameras.append(i)
    
    # Kiểm tra camera bằng đường dẫn thiết bị
    working_devices = []
    for device_path in devices:
        if test_direct_device(device_path):
            working_devices.append(device_path)
    
    # Tổng kết
    print("\n===== KẾT QUẢ KIỂM TRA =====")
    print(f"Tìm thấy {len(devices)} thiết bị camera")
    
    if working_cameras:
        print(f"Camera hoạt động tốt với chỉ số: {working_cameras}")
        print("Đề xuất: Sử dụng camera với chỉ số cụ thể khi chạy các script xác thực khuôn mặt:")
        print(f"  python scripts/collect_faces.py --username izzy --camera {working_cameras[0]}")
    else:
        print("Không tìm thấy camera nào hoạt động bằng chỉ số!")
    
    if working_devices:
        print(f"Thiết bị hoạt động tốt: {working_devices}")
        device_idx = working_devices[0].split('video')[1]
        print(f"Đề xuất: Sử dụng camera với chỉ số {device_idx} tương ứng với thiết bị {working_devices[0]}")
    else:
        print("Không tìm thấy thiết bị camera nào hoạt động trực tiếp!")
    
    if not (working_cameras or working_devices):
        print("\nGỢI Ý KHẮC PHỤC:")
        print("1. Kiểm tra kết nối vật lý của camera")
        print("2. Đảm bảo camera không bị ứng dụng khác sử dụng")
        print("3. Thử khởi động lại dịch vụ camera: sudo systemctl restart udev")
        print("4. Thử tải lại driver camera: sudo modprobe -r uvcvideo && sudo modprobe uvcvideo")
        print("5. Kiểm tra quyền truy cập: sudo usermod -a -G video $USER và đăng nhập lại")
        print("6. Kiểm tra camera với ứng dụng khác như 'cheese' hoặc 'guvcview'")

if __name__ == "__main__":
    main()