#!/usr/bin/env python3
import sys
# Thêm đường dẫn tới thư mục chứa module
sys.path.append('/usr/local/lib/face-auth')

try:
    import face_auth
    print("Module face_auth đã được import thành công!")
    print(f"Nằm ở đường dẫn: {face_auth.__file__}")
except ImportError as e:
    print(f"Lỗi khi import module face_auth: {e}")
    print("Đường dẫn Python hiện tại:")
    for path in sys.path:
        print(f"  - {path}")
