# Face Authentication System for Linux

Hệ thống xác thực khuôn mặt cho Linux, sử dụng OpenCV và face_recognition.

## Yêu cầu hệ thống

- Ubuntu 20.04 trở lên
- Python 3.8 trở lên
- Camera hoạt động

## Cài đặt

1. Cài đặt các thư viện hệ thống:
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev
sudo apt-get install -y cmake
sudo apt-get install -y libopenblas-dev liblapack-dev
sudo apt-get install -y libx11-dev libgtk-3-dev
sudo apt-get install -y python3-qt5
```

2. Cài đặt dlib:
```bash
pip3 install dlib
```

3. Cài đặt các thư viện Python cần thiết:
```bash
pip3 install face_recognition
pip3 install opencv-python
pip3 install PyQt5
```

4. Clone repository:
```bash
git clone <repository_url>
cd face_authentication_linux
```

## Cấu trúc thư mục

```
face_authentication_linux/
├── data/               # Thư mục chứa dữ liệu khuôn mặt
├── gui/               # Giao diện người dùng
│   ├── collect_faces.py    # Giao diện đăng ký khuôn mặt
│   └── authenticate.py     # Giao diện xác thực khuôn mặt
├── scripts/           # Các script xử lý
│   ├── collect_faces.py    # Xử lý thu thập khuôn mặt
│   ├── train_model.py      # Huấn luyện mô hình
│   ├── authenticate.py     # Xử lý xác thực
│   └── face_utils.py       # Các hàm tiện ích
└── README.md
```

## Sử dụng

### Đăng ký khuôn mặt mới

```bash
python3 gui/collect_faces.py --username <tên_người_dùng> --samples <số_lượng_ảnh>
```

Ví dụ:
```bash
python3 gui/collect_faces.py --username izzy --samples 20
```

### Xác thực khuôn mặt

```bash
python3 gui/authenticate.py
```

### Cài đặt tự động khởi động

1. Cấp quyền thực thi cho script cài đặt:
```bash
chmod +x install_service.sh
```

2. Chạy script cài đặt:
```bash
./install_service.sh
```

3. Khởi động service:
```bash
sudo systemctl start face-auth.service
```

4. Kiểm tra trạng thái:
```bash
sudo systemctl status face-auth.service
```

## Quản lý service

- Dừng service:
```bash
sudo systemctl stop face-auth.service
```

- Khởi động lại service:
```bash
sudo systemctl restart face-auth.service
```

- Vô hiệu hóa tự động khởi động:
```bash
sudo systemctl disable face-auth.service
```

## Xử lý sự cố

1. Nếu camera không hoạt động:
```bash
sudo usermod -a -G video $USER
```
Sau đó đăng xuất và đăng nhập lại.

2. Nếu gặp lỗi về quyền truy cập:
```bash
sudo chmod 666 /dev/video0
```

3. Kiểm tra camera:
```bash
ls -l /dev/video*
```

## Đóng góp

Mọi đóng góp đều được hoan nghênh. Vui lòng tạo issue hoặc pull request.

## Giấy phép

MIT License