#!/usr/bin/env python3
import tkinter as tk
import subprocess
import os
import sys
import time
import threading

# Lấy đường dẫn thư mục gốc của dự án
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(PROJECT_DIR, "venv", "bin", "python")
FACE_AUTH_SCRIPT = os.path.join(PROJECT_DIR, "scripts", "face_auth.py")
AUTH_TIMEOUT = 20  # Thời gian timeout cho xác thực (giây)

# Lấy tên người dùng hiện tại
try:
    CURRENT_USER = os.getlogin()
except OSError:
    # Fallback nếu getlogin không hoạt động
    CURRENT_USER = os.environ.get("USER", "unknown")

class FaceAuthWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Xác Thực Khuôn Mặt")
        self.root.attributes("-topmost", True)
        
        # Thiết lập kích thước cửa sổ và vị trí giữa màn hình
        window_width = 400
        window_height = 300
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        # Thiết lập màu nền tối cho giao diện
        self.root.configure(bg='#2e3440')
        
        # Tạo khung chứa nội dung
        main_frame = tk.Frame(root, bg='#2e3440', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Nhãn tiêu đề
        title_label = tk.Label(
            main_frame, 
            text="Xác Thực Khuôn Mặt", 
            font=("Arial", 18, "bold"), 
            bg='#2e3440', 
            fg='#eceff4'
        )
        title_label.pack(pady=(10, 20))
        
        # Nhãn thông tin người dùng
        self.user_label = tk.Label(
            main_frame, 
            text=f"Người dùng: {CURRENT_USER}", 
            font=("Arial", 12), 
            bg='#2e3440', 
            fg='#d8dee9'
        )
        self.user_label.pack(pady=5)
        
        # Nhãn trạng thái
        self.status_label = tk.Label(
            main_frame, 
            text="Nhấn nút bên dưới để xác thực", 
            font=("Arial", 11), 
            bg='#2e3440', 
            fg='#d8dee9'
        )
        self.status_label.pack(pady=10)
        
        # Khung hướng dẫn
        instruction_frame = tk.Frame(main_frame, bg='#3b4252', padx=15, pady=15, bd=1, relief=tk.SOLID)
        instruction_frame.pack(fill=tk.X, pady=10)
        
        instruction_text = tk.Label(
            instruction_frame, 
            text="Nhìn vào camera để xác thực khuôn mặt.\nGiữ khuôn mặt của bạn ở khoảng cách thích hợp\nvà đảm bảo ánh sáng đầy đủ.", 
            justify=tk.LEFT, 
            bg='#3b4252', 
            fg='#e5e9f0',
            font=("Arial", 10)
        )
        instruction_text.pack()
        
        # Nút xác thực
        self.auth_button = tk.Button(
            main_frame, 
            text="Quét Khuôn Mặt", 
            command=self.start_face_auth,
            bg='#5e81ac', 
            fg='white', 
            font=("Arial", 12, "bold"),
            padx=20,
            pady=10,
            bd=0,
            cursor="hand2"
        )
        self.auth_button.pack(pady=20)
        
        # Nút tùy chọn
        self.option_frame = tk.Frame(main_frame, bg='#2e3440')
        self.option_frame.pack(fill=tk.X, pady=5)
        
        self.cancel_button = tk.Button(
            self.option_frame, 
            text="Hủy", 
            command=self.cancel_auth,
            bg='#4c566a', 
            fg='white',
            padx=15,
            pady=5,
            bd=0
        )
        self.cancel_button.pack(side=tk.RIGHT)
        
        self.password_button = tk.Button(
            self.option_frame, 
            text="Đăng nhập bằng mật khẩu", 
            command=self.use_password,
            bg='#4c566a', 
            fg='white',
            padx=15,
            pady=5,
            bd=0
        )
        self.password_button.pack(side=tk.LEFT)
        
        # Biến theo dõi quy trình xác thực
        self.auth_in_progress = False
        self.auth_process = None
        
    def start_face_auth(self):
        """Bắt đầu quá trình xác thực khuôn mặt"""
        if self.auth_in_progress:
            return
        
        self.auth_in_progress = True
        self.auth_button.config(state=tk.DISABLED)
        self.status_label.config(text="Đang khởi tạo camera...", fg="#ebcb8b")
        
        # Chạy xác thực trong một luồng riêng để không làm đơ giao diện
        auth_thread = threading.Thread(target=self.run_face_auth)
        auth_thread.daemon = True
        auth_thread.start()
        
    def run_face_auth(self):
        """Chạy quy trình xác thực thực tế"""
        try:
            # Thiết lập đường dẫn để chạy script xác thực khuôn mặt
            if os.path.exists(VENV_PYTHON):
                python_cmd = VENV_PYTHON
            else:
                python_cmd = "python3"
                
            # Tạo lệnh thực thi
            cmd = [
                python_cmd, 
                FACE_AUTH_SCRIPT,
                "--username", 
                CURRENT_USER
            ]
            
            # Cập nhật giao diện
            self.root.after(0, lambda: self.status_label.config(
                text="Đang quét khuôn mặt... Vui lòng nhìn vào camera", 
                fg="#a3be8c"
            ))
            
            # Thực thi lệnh
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True
            )
            self.auth_process = process
            
            # Đặt timeout
            start_time = time.time()
            output = ""
            
            # Đọc output từ process
            while True:
                if process.poll() is not None:
                    # Process đã kết thúc
                    break
                    
                # Kiểm tra timeout
                if time.time() - start_time > AUTH_TIMEOUT:
                    process.terminate()
                    self.root.after(0, lambda: self.status_label.config(
                        text="Hết thời gian chờ xác thực", 
                        fg="#bf616a"
                    ))
                    break
                
                # Đọc output nếu có
                output_line = process.stdout.readline()
                if output_line:
                    output += output_line
                    
                time.sleep(0.1)
            
            # Xử lý kết quả
            if "SUCCESS" in output:
                self.root.after(0, lambda: self.status_label.config(
                    text="Xác thực thành công! Đang mở khóa...", 
                    fg="#a3be8c"
                ))
                # Thực hiện lệnh mở khóa màn hình
                self.unlock_screen()
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text="Xác thực thất bại. Vui lòng thử lại.", 
                    fg="#bf616a"
                ))
                self.root.after(0, lambda: self.auth_button.config(state=tk.NORMAL))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(
                text=f"Lỗi: {str(e)}", 
                fg="#bf616a"
            ))
            self.root.after(0, lambda: self.auth_button.config(state=tk.NORMAL))
        finally:
            self.auth_in_progress = False
            self.auth_process = None
    
    def unlock_screen(self):
        """Thực hiện lệnh mở khóa màn hình"""
        try:
            # Có thể sử dụng các lệnh khác nhau tùy thuộc vào môi trường desktop
            desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
            
            if 'gnome' in desktop_env:
                subprocess.run(['loginctl', 'unlock-session'])
            elif 'kde' in desktop_env:
                subprocess.run(['qdbus', 'org.kde.screensaver', '/ScreenSaver', 'org.freedesktop.ScreenSaver.Unlock'])
            elif 'xfce' in desktop_env:
                subprocess.run(['xfce4-screensaver-command', '--deactivate'])
            elif 'cinnamon' in desktop_env:
                subprocess.run(['cinnamon-screensaver-command', '--deactivate'])
            elif 'mate' in desktop_env:
                subprocess.run(['mate-screensaver-command', '--deactivate'])
            else:
                # Phương pháp dự phòng cho môi trường khác
                subprocess.run(['loginctl', 'unlock-session'])
                
            # Đóng cửa sổ xác thực
            self.root.after(1000, self.root.destroy)
            
        except Exception as e:
            self.status_label.config(
                text=f"Lỗi khi mở khóa: {str(e)}", 
                fg="#bf616a"
            )
            self.auth_button.config(state=tk.NORMAL)
    
    def cancel_auth(self):
        """Hủy quá trình xác thực và đóng ứng dụng"""
        if self.auth_process:
            try:
                self.auth_process.terminate()
            except:
                pass
        self.root.destroy()
    
    def use_password(self):
        """Chuyển sang phương thức xác thực bằng mật khẩu"""
        if self.auth_process:
            try:
                self.auth_process.terminate()
            except:
                pass
            
        desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
        
        try:
            # Khởi chạy màn hình nhập mật khẩu mặc định
            if 'gnome' in desktop_env:
                subprocess.Popen(['gdmflexiserver', '--startnew'])
            elif 'kde' in desktop_env:
                subprocess.Popen(['qdbus', 'org.kde.ksmserver', '/KSMServer', 'org.kde.KSMServerInterface.openSwitchUserDialog'])
            else:
                # Phương pháp dự phòng cho các môi trường khác
                subprocess.Popen(['dm-tool', 'switch-to-greeter'])
                
            # Đóng cửa sổ hiện tại
            self.root.destroy()
        except Exception as e:
            self.status_label.config(
                text=f"Không thể chuyển đổi: {str(e)}", 
                fg="#bf616a"
            )

def main():
    root = tk.Tk()
    app = FaceAuthWindow(root)
    
    # Thiết lập để đóng cửa sổ khi nhấn phím Escape
    root.bind('<Escape>', lambda e: root.destroy())
    
    # Cài đặt màn hình toàn cảnh (fullscreen) nếu cần
    # root.attributes('-fullscreen', True)
    
    root.mainloop()

if __name__ == "__main__":
    main()