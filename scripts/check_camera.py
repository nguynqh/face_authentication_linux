#!/usr/bin/env python3
import cv2
import time
import os
import sys

def check_camera_backends():
    """Kiểm tra các backend camera có sẵn trong OpenCV"""
    print("Các backend camera OpenCV được hỗ trợ:")
    backends = [
        (cv2.CAP_ANY, "Auto"),
        (cv2.CAP_V4L2, "Video for Linux 2"),
        (cv2.CAP_V4L, "Video for Linux 1"),
        (cv2.CAP_GSTREAMER, "GStreamer"),
        (cv2.CAP_FFMPEG, "FFmpeg")
    ]
    
    for backend, name in backends:
        if cv2.__version__.startswith('4'):
            is_built = cv2.videoio_registry.hasBackend(backend)
            print(f"- {name}: {'Supported' if is_built else 'Not supported'}")
        else:
            print(f"- {name}: Không xác định (yêu cầu OpenCV 4+)")

def test_camera_with_backend(camera_index, backend=None):
    """Kiểm tra camera với backend cụ thể"""
    try:
        if backend:
            print(f"Thử mở camera {camera_index} với backend {backend}...")
            cap = cv2.VideoCapture(camera_index, backend)
        else:
            print(f"Thử mở camera {camera_index} với backend mặc định...")
            cap = cv2.VideoCapture(camera_index)
            
        if not cap.isOpened():
            print(f"Không thể mở camera {camera_index}")
            return False
            
        print(f"Camera {camera_index} đã mở thành công!")
        
        # Đọc một số frame để kiểm tra
        success_count = 0
        for i in range(5):
            ret, frame = cap.read()
            if ret:
                success_count += 1
                print(f"  Frame {i+1}: OK - Kích thước {frame.shape[1]}x{frame.shape[0]}")
            else:
                print(f"  Frame {i+1}: THẤT BẠI")
            time.sleep(0.5)
            
        print(f"Đọc thành công {success_count}/5 frame")
        
        # Hiển thị thông tin về camera
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"Thông tin camera:")
        print(f"- Độ phân giải: {width}x{height}")
        print(f"- FPS: {fps}")
        print(f"- Backend được sử dụng: {cap.getBackendName()}")
        
        # Hiển thị frame cuối cùng
        if success_count > 0 and os.environ.get('DISPLAY'):
            cv2.imshow(f"Camera {camera_index} Test", frame)
            print("Hiển thị khung hình kiểm tra. Nhấn phím bất kỳ để đóng.")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
        return success_count > 0
    except Exception as e:
        print(f"Lỗi khi kiểm tra camera {camera_index}: {e}")
        return False
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()

def check_device_files():
    """Kiểm tra các file thiết bị video có sẵn"""
    import glob
    import subprocess
    
    print("\nCác thiết bị video có sẵn:")
    video_devices = glob.glob('/dev/video*')
    if not video_devices:
        print("Không tìm thấy thiết bị video nào!")
        return
        
    for device in sorted(video_devices):
        try:
            # Dùng v4l2-ctl để lấy thông tin chi tiết hơn về thiết bị
            result = subprocess.run(['v4l2-ctl', '--device', device, '--info'], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True, timeout=3)
            
            if result.returncode == 0:
                # Trích xuất tên thiết bị
                for line in result.stdout.split('\n'):
                    if 'Card type' in line:
                        print(f"{device}: {line.split(':')[1].strip()}")
                        break
                else:
                    print(f"{device}: Thiết bị video")
            else:
                print(f"{device}: Không thể đọc thông tin (cần cài đặt v4l-utils)")
        except FileNotFoundError:
            print(f"{device}: Thiết bị video (cần cài đặt v4l-utils để biết thêm chi tiết)")
        except Exception as e:
            print(f"{device}: Lỗi khi đọc thông tin - {str(e)}")

def check_camera_permissions():
    """Kiểm tra quyền truy cập vào các thiết bị camera"""
    import glob
    import os
    import pwd
    import grp
    
    print("\nKiểm tra quyền truy cập thiết bị camera:")
    username = os.getlogin()
    user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    user_groups.append(pwd.getpwnam(username).pw_name)  # Add primary group
    
    print(f"Người dùng hiện tại: {username}")
    print(f"Các nhóm: {', '.join(user_groups)}")
    
    video_devices = glob.glob('/dev/video*')
    if not video_devices:
        print("Không tìm thấy thiết bị video nào!")
        return
        
    for device in sorted(video_devices):
        try:
            stat_info = os.stat(device)
            device_group = grp.getgrgid(stat_info.st_gid).gr_name
            permissions = oct(stat_info.st_mode)[-3:]
            
            print(f"{device}:")
            print(f"  - Nhóm sở hữu: {device_group}")
            print(f"  - Quyền: {permissions}")
            
            # Kiểm tra xem người dùng có quyền truy cập hay không
            can_access = device_group in user_groups or (stat_info.st_mode & 0o007) != 0
            if can_access:
                print("  - Quyền truy cập: CÓ")
            else:
                print("  - Quyền truy cập: KHÔNG")
                print("  - Giải pháp: Thêm người dùng vào nhóm 'video' với lệnh 'sudo usermod -a -G video $USER'")
        except Exception as e:
            print(f"{device}: Lỗi khi kiểm tra quyền - {str(e)}")

def check_running_processes():
    """Kiểm tra các tiến trình đang sử dụng camera"""
    import subprocess
    
    print("\nCác tiến trình đang sử dụng thiết bị video:")
    try:
        result = subprocess.run(['fuser', '-v', '/dev/video*'], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                               text=True)
        
        if result.stderr and 'No such file' not in result.stderr:
            print(result.stderr.strip())
        elif result.stdout:
            print(result.stdout.strip())
        else:
            print("Không có tiến trình nào đang sử dụng các thiết bị video")
    except FileNotFoundError:
        print("Không thể kiểm tra (cần cài đặt 'fuser' bằng lệnh 'sudo apt install psmisc')")
    except Exception as e:
        print(f"Lỗi khi kiểm tra tiến trình: {str(e)}")

def check_kernel_modules():
    """Kiểm tra các module kernel liên quan đến camera"""
    import subprocess
    
    print("\nKiểm tra các module kernel liên quan đến camera:")
    try:
        # Kiểm tra uvcvideo module
        result = subprocess.run(['lsmod'], stdout=subprocess.PIPE, text=True)
        if 'uvcvideo' in result.stdout:
            print("✅ Module uvcvideo đã được tải")
            
            # Hiển thị thông tin chi tiết hơn
            details = subprocess.run(['modinfo', 'uvcvideo'], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True)
            if details.returncode == 0:
                for line in details.stdout.split('\n'):
                    if line.startswith('version:') or line.startswith('description:'):
                        print(f"  - {line.strip()}")
        else:
            print("❌ Module uvcvideo chưa được tải! Đây có thể là nguyên nhân camera không hoạt động")
            print("  - Giải pháp: Tải module với lệnh 'sudo modprobe uvcvideo'")

        # Kiểm tra các module video khác
        video_modules = ['videodev', 'v4l2_common']
        for module in video_modules:
            if module in result.stdout:
                print(f"✅ Module {module} đã được tải")
            else:
                print(f"❌ Module {module} chưa được tải")
    except Exception as e:
        print(f"Lỗi khi kiểm tra module kernel: {str(e)}")

def check_device_access():
    """Kiểm tra truy cập trực tiếp vào thiết bị camera"""
    import os
    import glob
    
    print("\nKiểm tra truy cập trực tiếp vào thiết bị camera:")
    video_devices = glob.glob('/dev/video*')
    if not video_devices:
        print("Không tìm thấy thiết bị video nào!")
        return
        
    for device in sorted(video_devices):
        try:
            with open(device, 'rb') as f:
                # Chỉ thử mở thiết bị, không đọc dữ liệu
                print(f"✅ Có thể mở {device} để đọc")
        except PermissionError:
            print(f"❌ Không có quyền mở {device}")
        except Exception as e:
            print(f"❌ Không thể mở {device}: {str(e)}")

def check_desktop_environment():
    """Kiểm tra môi trường desktop và biến môi trường liên quan"""
    import os
    print("\nKiểm tra môi trường desktop:")
    
    # Kiểm tra DISPLAY
    display = os.environ.get('DISPLAY')
    print(f"DISPLAY: {display if display else 'Không được thiết lập'}")
    
    # Kiểm tra XDG_SESSION_TYPE
    session_type = os.environ.get('XDG_SESSION_TYPE')
    print(f"XDG_SESSION_TYPE: {session_type if session_type else 'Không được thiết lập'}")
    
    # Kiểm tra biến PAM_SERVICE nếu đang chạy trong ngữ cảnh PAM
    pam_service = os.environ.get('PAM_SERVICE')
    if pam_service:
        print(f"Đang chạy trong ngữ cảnh PAM: {pam_service}")
    
    # Kiểm tra wayland vs x11
    wayland_display = os.environ.get('WAYLAND_DISPLAY')
    if wayland_display:
        print("Đang sử dụng Wayland display server")
    elif display:
        print("Đang sử dụng X11 display server")
    else:
        print("Không tìm thấy display server")

def check_opencv_installation():
    """Kiểm tra thông tin cài đặt OpenCV"""
    import cv2
    import sys
    import subprocess
    
    print("\nThông tin cài đặt OpenCV:")
    print(f"Phiên bản OpenCV: {cv2.__version__}")
    
    # Hiển thị đường dẫn cài đặt
    print(f"OpenCV được cài đặt tại: {cv2.__file__}")
    
    # Kiểm tra các khả năng của OpenCV
    print("\nKhả năng của OpenCV:")
    has_gstreamer = cv2.getBuildInformation() if hasattr(cv2, 'getBuildInformation') else ""
    print(f"- GStreamer: {'YES' if 'GStreamer: YES' in has_gstreamer else 'NO'}")
    print(f"- V4L/V4L2: {'YES' if 'V4L/V4L2: YES' in has_gstreamer else 'NO'}")
    
    # Kiểm tra các gói Python liên quan đến camera được cài đặt
    print("\nCác gói Python liên quan đến camera:")
    try:
        import pkg_resources
        relevant_packages = ['opencv-python', 'opencv-contrib-python', 'v4l2', 'pygobject', 'pyv4l2', 'pillow']
        for package in relevant_packages:
            try:
                version = pkg_resources.get_distribution(package).version
                print(f"- {package}: {version}")
            except pkg_resources.DistributionNotFound:
                print(f"- {package}: Không được cài đặt")
    except ImportError:
        print("Không thể kiểm tra các gói được cài đặt (setuptools không có sẵn)")

def test_camera_with_direct_approaches():
    """Thử các phương pháp trực tiếp khác nhau để kiểm tra camera"""
    import subprocess
    print("\nKiểm tra camera với các phương pháp thay thế:")
    
    # Phương pháp 1: ffplay
    print("\n1. Kiểm tra với FFmpeg/FFplay:")
    try:
        # Chỉ kiểm tra ffplay có tồn tại không, không thực sự chạy nó
        result = subprocess.run(['which', 'ffplay'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True)
        if result.returncode == 0:
            print(f"✅ ffplay được cài đặt tại: {result.stdout.strip()}")
            print("Bạn có thể kiểm tra camera bằng lệnh sau:")
            print("ffplay -f v4l2 -framerate 30 -video_size 640x480 -i /dev/video0")
        else:
            print("❌ ffplay không được cài đặt")
            print("Bạn có thể cài đặt bằng: sudo apt install ffmpeg")
    except Exception as e:
        print(f"Lỗi khi kiểm tra ffplay: {str(e)}")
    
    # Phương pháp 2: v4l2-ctl
    print("\n2. Kiểm tra với v4l2-ctl:")
    try:
        result = subprocess.run(['which', 'v4l2-ctl'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True)
        if result.returncode == 0:
            print(f"✅ v4l2-ctl được cài đặt tại: {result.stdout.strip()}")
            print("Để liệt kê các thiết bị và kiểm tra khả năng, sử dụng:")
            print("v4l2-ctl --list-devices")
            print("v4l2-ctl -d /dev/video0 --list-formats-ext")
        else:
            print("❌ v4l2-ctl không được cài đặt")
            print("Bạn có thể cài đặt bằng: sudo apt install v4l-utils")
    except Exception as e:
        print(f"Lỗi khi kiểm tra v4l2-ctl: {str(e)}")
    
    # Phương pháp 3: gst-launch
    print("\n3. Kiểm tra với GStreamer:")
    try:
        result = subprocess.run(['which', 'gst-launch-1.0'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True)
        if result.returncode == 0:
            print(f"✅ gst-launch-1.0 được cài đặt tại: {result.stdout.strip()}")
            print("Để kiểm tra camera với GStreamer, sử dụng:")
            print("gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink")
        else:
            print("❌ gst-launch-1.0 không được cài đặt")
            print("Bạn có thể cài đặt bằng: sudo apt install gstreamer1.0-tools")
    except Exception as e:
        print(f"Lỗi khi kiểm tra GStreamer: {str(e)}")

def main():
    print("=== CHƯƠNG TRÌNH KIỂM TRA CAMERA NÂNG CAO ===")
    print("Phiên bản OpenCV:", cv2.__version__)
    
    # Kiểm tra cài đặt OpenCV
    check_opencv_installation()
    
    # Kiểm tra môi trường desktop
    check_desktop_environment()
    
    # Kiểm tra các backend camera
    check_camera_backends()
    
    # Kiểm tra module kernel
    check_kernel_modules()
    
    # Kiểm tra các thiết bị camera
    check_device_files()
    
    # Kiểm tra quyền truy cập camera
    check_camera_permissions()
    
    # Kiểm tra truy cập trực tiếp
    check_device_access()
    
    # Kiểm tra các tiến trình đang sử dụng camera
    check_running_processes()
    
    # Thử các phương pháp kiểm tra camera thay thế
    test_camera_with_direct_approaches()
    
    # Kiểm tra với OpenCV
    print("\n=== KIỂM TRA CAMERA VỚI OPENCV ===")
    # Kiểm tra từng camera
    camera_found = False
    for camera_index in range(3):  # Thử camera 0, 1, và 2
        # Thử với các backend khác nhau
        backends = [None, cv2.CAP_V4L2, cv2.CAP_V4L, cv2.CAP_GSTREAMER, cv2.CAP_FFMPEG]
        for backend in backends:
            if test_camera_with_backend(camera_index, backend):
                camera_found = True
                break
    
    if not camera_found:
        print("\n❌ KHÔNG THỂ TRUY CẬP BẤT KỲ CAMERA NÀO!")
        print("\nGIẢI PHÁP CÓ THỂ THỰC HIỆN:")
        print("1. Kiểm tra kết nối vật lý camera")
        print("2. Thêm người dùng vào nhóm 'video': sudo usermod -a -G video $USER")
        print("3. Đảm bảo module kernel đã được tải: sudo modprobe uvcvideo")
        print("4. Đặt quyền cho thiết bị: sudo chmod 666 /dev/video*")
        print("5. Cài đặt v4l-utils: sudo apt install v4l-utils")
        print("6. Kiểm tra log kernel với: dmesg | grep -i video")
        print("7. Khởi động lại máy sau khi thực hiện các thay đổi")
    else:
        print("\n✅ ĐÃ TÌM THẤY VÀ TRUY CẬP THÀNH CÔNG CAMERA!")

if __name__ == "__main__":
    main()