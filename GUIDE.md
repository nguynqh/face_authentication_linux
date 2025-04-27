# 🔐 Hướng Dẫn Cài Đặt Hệ Thống Xác Thực Khuôn Mặt Cho Ubuntu

Tài liệu này hướng dẫn chi tiết cách cài đặt và sử dụng hệ thống xác thực khuôn mặt trên Ubuntu. Hệ thống này cho phép bạn đăng nhập vào máy tính, mở khóa màn hình và sử dụng các lệnh `sudo` bằng cách nhận diện khuôn mặt của bạn thay vì nhập mật khẩu.

## 📋 Mục Lục

1. [Yêu Cầu Hệ Thống](#yêu-cầu-hệ-thống)
2. [Cài Đặt](#cài-đặt)
3. [Cấu Hình](#cấu-hình)
4. [Thu Thập Dữ Liệu Khuôn Mặt](#thu-thập-dữ-liệu-khuôn-mặt)
5. [Huấn Luyện Mô Hình](#huấn-luyện-mô-hình)
6. [Tích Hợp Vào Hệ Thống](#tích-hợp-vào-hệ-thống)
7. [Cấu Hình Xác Thực Tại Màn Hình Đăng Nhập](#cấu-hình-xác-thực-tại-màn-hình-đăng-nhập)
8. [Cách Sử Dụng](#cách-sử-dụng)
9. [Xử Lý Sự Cố](#xử-lý-sự-cố)

## Yêu Cầu Hệ Thống

- **Hệ điều hành**: Ubuntu hoặc các distro dựa trên Debian
- **Camera**: Webcam hoặc camera tích hợp trên máy tính
- **Python**: Phiên bản 3.6 trở lên
- **Quyền administrator** (sudo) để cài đặt các gói và thay đổi cấu hình PAM

## Cài Đặt

### Bước 1: Cài đặt các gói phụ thuộc của hệ thống

```bash
# Cập nhật danh sách gói
sudo apt update

# Cài đặt các gói phụ thuộc cần thiết
sudo apt install -y python3-pip python3-dev cmake build-essential pkg-config
sudo apt install -y libopencv-dev
sudo apt install -y libdlib-dev
sudo apt install -y python3-venv
sudo apt install -y libpam0g-dev
```

### Bước 2: Tải mã nguồn

```bash
# Tải mã nguồn từ GitHub hoặc sao chép từ ổ cứng
git clone https://github.com/your-username/face_authentication_linux.git
cd face_authentication_linux
```

### Bước 3: Tạo môi trường ảo và cài đặt các gói Python

```bash
# Tạo môi trường ảo Python
python3 -m venv venv

# Kích hoạt môi trường ảo
source venv/bin/activate

# Cài đặt các gói Python cần thiết
pip install numpy scikit-learn scikit-image pillow
pip install tensorflow
pip install face_recognition dlib opencv-python
```

## Cấu Hình

### Bước 1: Chỉnh sửa đường dẫn trong các file

Hãy đảm bảo rằng các đường dẫn trong các file đã được cập nhật chính xác:

1. Trong file `pam_module/pam_face_auth.c`, thay thế đường dẫn `FACE_AUTH_SCRIPT` bằng đường dẫn tới script `start_face_auth.sh` của bạn:
   ```c
   #define FACE_AUTH_SCRIPT "/home/your-username/face_authentication_linux/start_face_auth.sh"
   ```

2. Trong file `start_face_auth.sh`, kiểm tra đường dẫn đến thư mục dự án:
   ```bash
   cd /home/your-username/face_authentication_linux || exit 1
   ```

### Bước 2: Cấp quyền thực thi cho các script

```bash
chmod +x start_face_auth.sh
chmod +x scripts/collect_faces.py
chmod +x scripts/train_model.py
chmod +x scripts/face_auth.py
chmod +x scripts/gui.py
chmod +x face_auth_helper.sh
chmod +x setup_login_auth.sh
```

## Thu Thập Dữ Liệu Khuôn Mặt

### Phương Pháp 1: Sử dụng Giao diện đồ họa

1. Khởi động giao diện quản lý:
   ```bash
   source venv/bin/activate
   python scripts/gui.py
   ```

2. Nhấn nút "Thu thập Khuôn mặt" trên giao diện.

3. Khi cửa sổ camera hiện ra, nhấn phím 's' để bắt đầu thu thập dữ liệu.

4. Đứng trước camera và đảm bảo khuôn mặt của bạn hiện rõ. Hệ thống sẽ tự động chụp 20 ảnh (mặc định).

5. Sau khi hoàn tất, nhấn phím 'q' hoặc đợi đến khi đủ số lượng ảnh.

### Phương Pháp 2: Sử dụng Command line

```bash
source venv/bin/activate
python scripts/collect_faces.py --username your-username --samples 20
```

## Huấn Luyện Mô Hình

### Phương Pháp 1: Sử dụng Giao diện đồ họa

1. Trong giao diện quản lý, nhấn nút "Huấn luyện Mô hình".
2. Đợi quá trình huấn luyện hoàn tất.

### Phương Pháp 2: Sử dụng Command line

```bash
source venv/bin/activate
python scripts/train_model.py
```

## Tích Hợp Vào Hệ Thống

### Bước 1: Biên dịch và cài đặt module PAM

```bash
cd pam_module
make
sudo make install
cd ..
```

### Bước 2: Cài đặt helper script

```bash
sudo cp face_auth_helper.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/face_auth_helper.sh
```

### Bước 3: Cấu hình PAM để sử dụng xác thực khuôn mặt

```bash
# Sao lưu file cấu hình PAM hiện tại
sudo cp /etc/pam.d/common-auth /etc/pam.d/common-auth.backup

# Chỉnh sửa file cấu hình PAM
sudo nano /etc/pam.d/common-auth
```

Thêm dòng sau vào **đầu file** (hoặc trước dòng `@include common-auth` nếu có):

```
auth sufficient pam_exec.so expose_authtok user=your-username /usr/local/bin/face_auth_helper.sh
auth sufficient pam_face_auth.so
```

Thay thế `your-username` bằng tên người dùng thực tế của bạn.

### Bước 4: Thiết lập tự động khởi động giao diện

Để giao diện quản lý tự động khởi động khi đăng nhập:

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/face-auth-gui.desktop << EOL
[Desktop Entry]
Type=Application
Name=Face Auth GUI
Comment=Quản lý Xác thực Khuôn mặt
Exec=/home/your-username/face_authentication_linux/venv/bin/python /home/your-username/face_authentication_linux/scripts/gui.py
Icon=system-users
Terminal=false
Categories=Utility;Application;
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOL

chmod +x ~/.config/autostart/face-auth-gui.desktop
```

Nhớ thay thế `your-username` bằng tên người dùng thực tế của bạn.

## Cấu Hình Xác Thực Tại Màn Hình Đăng Nhập

Để hệ thống xác thực khuôn mặt hoạt động ngay tại màn hình đăng nhập (trước khi đăng nhập vào hệ thống), bạn cần cấu hình thêm module PAM cho GDM (GNOME Display Manager).

### Sử dụng script tự động

Để tiện lợi, hệ thống cung cấp script tự động `setup_login_auth.sh` để cấu hình:

```bash
# Cấp quyền thực thi cho script (nếu chưa có)
chmod +x setup_login_auth.sh

# Chạy script với quyền sudo
sudo ./setup_login_auth.sh
```

Script này sẽ tự động thêm cấu hình xác thực khuôn mặt vào file `/etc/pam.d/gdm-password` để kích hoạt tính năng xác thực khuôn mặt tại màn hình đăng nhập.

### Cấu hình thủ công (nếu không sử dụng script)

Nếu bạn muốn cấu hình thủ công:

```bash
# Sao lưu file cấu hình GDM
sudo cp /etc/pam.d/gdm-password /etc/pam.d/gdm-password.backup

# Chỉnh sửa file cấu hình
sudo nano /etc/pam.d/gdm-password
```

Thêm các dòng sau vào đầu file:

```
# Xác thực khuôn mặt cho GDM
auth sufficient pam_exec.so expose_authtok /usr/local/bin/face_auth_helper.sh
auth sufficient pam_face_auth.so
```

### Kiểm tra sau khi cấu hình

1. Sau khi cấu hình, khởi động lại hệ thống để áp dụng thay đổi:
   ```bash
   sudo reboot
   ```

2. Tại màn hình đăng nhập, hệ thống sẽ tự động kích hoạt camera và thử xác thực khuôn mặt.

3. Nếu nhận diện thành công, bạn sẽ được đăng nhập vào hệ thống mà không cần nhập mật khẩu.

## Cách Sử Dụng

Sau khi hoàn tất thiết lập, bạn có thể sử dụng xác thực khuôn mặt trong các trường hợp sau:

1. **Đăng nhập vào hệ thống**: Tại màn hình đăng nhập, camera sẽ tự động kích hoạt để nhận diện khuôn mặt của bạn.

2. **Mở khóa màn hình**: Khi màn hình bị khóa, camera sẽ tự động kích hoạt để nhận diện khuôn mặt của bạn.

3. **Sử dụng sudo**: Khi chạy lệnh với `sudo`, camera sẽ được kích hoạt để xác thực thay vì yêu cầu nhập mật khẩu.

Trong trường hợp xác thực khuôn mặt thất bại (ví dụ: ánh sáng không đủ hoặc camera không hoạt động), hệ thống sẽ yêu cầu mật khẩu như thông thường.

## Xử Lý Sự Cố

### Camera không hoạt động

Nếu camera không hoạt động, hãy kiểm tra:

1. Camera đã được kết nối và hoạt động:
   ```bash
   ls -l /dev/video*
   ```

2. Cập nhật các camera index trong files:
   - `scripts/collect_faces.py`
   - `scripts/face_auth.py` 
   
   Thay đổi chỉ số camera (`cv2.VideoCapture(1)`) thành chỉ số phù hợp với camera của bạn.

### Lỗi tại màn hình đăng nhập

Nếu xác thực khuôn mặt không hoạt động tại màn hình đăng nhập:

1. Kiểm tra các biến môi trường trong file helper script (`/usr/local/bin/face_auth_helper.sh`)
2. Đảm bảo camera không bị khóa bởi ứng dụng khác
3. Kiểm tra log xác thực:
   ```bash
   cat /tmp/face_auth.log
   ```

### Khôi phục cấu hình PAM gốc

Nếu gặp sự cố với xác thực PAM và không thể đăng nhập:

1. Khởi động vào chế độ khôi phục (recovery mode)
2. Mount filesystem với quyền ghi:
   ```bash
   mount -o remount,rw /
   ```
3. Khôi phục file PAM gốc:
   ```bash
   cp /etc/pam.d/common-auth.backup /etc/pam.d/common-auth
   cp /etc/pam.d/gdm-password.backup /etc/pam.d/gdm-password
   ```

### Kiểm tra hiệu năng của mô hình nhận dạng

Nếu camera hoạt động nhưng xác thực luôn thất bại:

1. Kiểm tra điều kiện ánh sáng - đảm bảo khuôn mặt được chiếu sáng đầy đủ
2. Thu thập lại dữ liệu khuôn mặt với nhiều góc độ và điều kiện ánh sáng khác nhau
3. Điều chỉnh ngưỡng tin cậy trong `face_auth.py` thành giá trị thấp hơn (mặc định: 0.6):
   ```bash
   python scripts/face_auth.py --username your-username --threshold 0.5
   ```

---

## Lưu Ý Bảo Mật

- Hệ thống xác thực khuôn mặt nên được coi là tính năng tiện lợi và không nên dùng cho các hệ thống với yêu cầu bảo mật cao.
- Xác thực khuôn mặt có thể bị ảnh hưởng bởi điều kiện ánh sáng và chất lượng camera.
- Luôn đảm bảo bạn có phương pháp xác thực dự phòng (mật khẩu).
- Định kỳ cập nhật dữ liệu khuôn mặt để duy trì độ chính xác của hệ thống.