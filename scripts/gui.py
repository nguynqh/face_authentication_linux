#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import os
import threading

# Lấy đường dẫn thư mục gốc của dự án
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(PROJECT_DIR, "venv", "bin", "python")
COLLECT_SCRIPT = os.path.join(PROJECT_DIR, "scripts", "collect_faces.py")
TRAIN_SCRIPT = os.path.join(PROJECT_DIR, "scripts", "train_model.py")

# Lấy tên người dùng hiện tại
try:
    CURRENT_USER = os.getlogin()
except OSError:
    # Fallback nếu getlogin không hoạt động (ví dụ: chạy qua sudo)
    CURRENT_USER = os.environ.get("USER", "unknown")

def run_script(script_path, args=[], output_widget=None):
    """Chạy một script Python trong virtualenv và hiển thị output."""
    command = [VENV_PYTHON, script_path] + args
    
    def task():
        try:
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1, 
                universal_newlines=True,
                cwd=PROJECT_DIR # Đảm bảo chạy từ thư mục gốc dự án
            )
            
            if output_widget:
                output_widget.config(state=tk.NORMAL)
                output_widget.delete(1.0, tk.END)
                output_widget.insert(tk.END, f"Đang chạy: {' '.join(command)}")
                output_widget.config(state=tk.DISABLED)

            for line in process.stdout:
                if output_widget:
                    output_widget.config(state=tk.NORMAL)
                    output_widget.insert(tk.END, line)
                    output_widget.see(tk.END) # Cuộn xuống dòng cuối
                    output_widget.config(state=tk.DISABLED)
                    output_widget.update_idletasks() # Cập nhật giao diện

            process.wait()
            
            if output_widget:
                 output_widget.config(state=tk.NORMAL)
                 output_widget.insert(tk.END, f"Hoàn thành với mã thoát: {process.returncode}")
                 output_widget.config(state=tk.DISABLED)

            if process.returncode == 0:
                messagebox.showinfo("Thành công", f"Script {os.path.basename(script_path)} đã chạy thành công.")
            else:
                 messagebox.showerror("Lỗi", f"Script {os.path.basename(script_path)} đã gặp lỗi (mã: {process.returncode}). Xem chi tiết trong cửa sổ output.")

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể chạy script: {e}")
            if output_widget:
                 output_widget.config(state=tk.NORMAL)
                 output_widget.insert(tk.END, f"Lỗi khi chạy: {e}")
                 output_widget.config(state=tk.DISABLED)
        finally:
            # Kích hoạt lại các nút sau khi chạy xong
            collect_button.config(state=tk.NORMAL)
            train_button.config(state=tk.NORMAL)

    # Vô hiệu hóa các nút khi đang chạy
    collect_button.config(state=tk.DISABLED)
    train_button.config(state=tk.DISABLED)
    
    # Chạy trong một thread riêng để không chặn giao diện chính
    thread = threading.Thread(target=task)
    thread.start()

def collect_faces():
    run_script(COLLECT_SCRIPT, ["--username", CURRENT_USER], output_text)

def train_model():
    run_script(TRAIN_SCRIPT, output_widget=output_text)

# --- Giao diện Tkinter ---
root = tk.Tk()
root.title("Quản lý Xác thực Khuôn mặt")
root.geometry("600x450") # Kích thước cửa sổ

main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# Frame cho các nút
button_frame = tk.Frame(main_frame)
button_frame.pack(pady=10)

# Nhãn thông tin người dùng
user_label = tk.Label(button_frame, text=f"Người dùng hiện tại: {CURRENT_USER}")
user_label.pack(side=tk.LEFT, padx=10)

# Nút Thu thập Khuôn mặt
collect_button = tk.Button(button_frame, text="Thu thập Khuôn mặt", command=collect_faces)
collect_button.pack(side=tk.LEFT, padx=5)

# Nút Huấn luyện Mô hình
train_button = tk.Button(button_frame, text="Huấn luyện Mô hình", command=train_model)
train_button.pack(side=tk.LEFT, padx=5)

# Khung chứa output
output_frame = tk.LabelFrame(main_frame, text="Output", padx=5, pady=5)
output_frame.pack(fill=tk.BOTH, expand=True)

# Vùng văn bản hiển thị output (có thanh cuộn)
output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED, height=15)
output_text.pack(fill=tk.BOTH, expand=True)

root.mainloop()

