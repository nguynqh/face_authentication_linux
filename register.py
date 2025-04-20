#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf, Pango
import cv2
import os
import sys
import time
import numpy as np
import face_recognition
import threading
import logging
from pathlib import Path

# Import module xử lý chung
sys.path.append('/usr/lib/face-auth')
from common import (
    save_face_encoding, is_face_registered, ensure_data_dir,
    calculate_ear, logger, EAR_THRESHOLD, SHARPNESS_THRESHOLD
)

class FaceRegistrationWindow(Gtk.Window):
    def __init__(self, username=None):
        Gtk.Window.__init__(self, title="Đăng ký xác thực khuôn mặt")
        self.set_default_size(800, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Lấy username
        self.username = username if username else os.environ.get('USER')
        
        # Khởi tạo biến
        self.cap = None
        self.running = True
        self.registering = False
        self.blink_count = 0
        self.eye_closed_frames = 0
        self.eye_open_frames = 0
        self.face_verified = False
        
        # Setup UI
        self.setup_ui()
        
        # Kiểm tra xem đã đăng ký chưa
        if is_face_registered(self.username):
            self.show_registered_dialog()
        else:
            # Bắt đầu camera
            self.start_camera()
    
    def setup_ui(self):
        # Main Grid
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_margin_start(20)
        grid.set_margin_end(20)
        grid.set_margin_top(20)
        grid.set_margin_bottom(20)
        self.add(grid)
        
        # Camera display
        self.camera_image = Gtk.Image()
        self.camera_image.set_size_request(640, 480)
        
        # Khung camera
        frame = Gtk.Frame(label="Camera")
        frame.add(self.camera_image)
        grid.attach(frame, 0, 0, 2, 1)
        
        # Hướng dẫn
        instructions = Gtk.Label()
        instructions.set_markup(
            "<span size='large'><b>Hướng dẫn đăng ký:</b></span>\n\n"
            "1. Đặt khuôn mặt của bạn vào giữa khung hình\n"
            "2. Di chuyển đầu nhẹ nhàng theo hướng dẫn\n"
            "3. Chớp mắt ít nhất 3 lần\n"
            "4. Nhấn nút 'Đăng ký' khi hoàn tất\n\n"
            "<i>Lưu ý: Cần đủ ánh sáng và đảm bảo hình ảnh rõ nét</i>"
        )
        instructions.set_line_wrap(True)
        instructions.set_xalign(0)
        grid.attach(instructions, 0, 1, 1, 1)
        
        # Thông tin trạng thái
        self.status_label = Gtk.Label(label="Đang khởi tạo camera...")
        self.status_label.set_xalign(0)
        grid.attach(self.status_label, 1, 1, 1, 1)
        
        # Nút Đăng ký
        self.register_button = Gtk.Button(label="Đăng ký")
        self.register_button.connect("clicked", self.on_register_clicked)
        self.register_button.set_sensitive(False)
        
        # Nút Hủy
        cancel_button = Gtk.Button(label="Hủy")
        cancel_button.connect("clicked", self.on_cancel_clicked)
        
        # Box chứa các nút
        button_box = Gtk.Box(spacing=10)
        button_box.pack_end(self.register_button, False, False, 0)
        button_box.pack_end(cancel_button, False, False, 0)
        grid.attach(button_box, 0, 2, 2, 1)
    
    def show_registered_dialog(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Bạn đã đăng ký khuôn mặt"
        )
        dialog.format_secondary_text("Bạn có muốn đăng ký lại không?")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Bắt đầu camera
            self.start_camera()
        else:
            self.destroy()
    
    def start_camera(self):
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.show_error_dialog("Không thể mở camera")
                return
            
            # Cập nhật trạng thái
            self.status_label.set_text("Hãy nhìn vào camera và chớp mắt ít nhất 3 lần...")
            
            # Bắt đầu thread xử lý camera
            self.camera_thread = threading.Thread(target=self.process_camera)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
            # Timer cập nhật UI
            GLib.timeout_add(33, self.update_ui)
            
        except Exception as e:
            self.show_error_dialog(f"Lỗi khởi tạo camera: {str(e)}")
    
    def process_camera(self):
        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                # Xử lý frame
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Phát hiện khuôn mặt
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if face_locations:
                    # Vẽ khung mặt
                    top, right, bottom, left = face_locations[0]
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    
                    # Kiểm tra độ sắc nét
                    face_crop = gray[top:bottom, left:right]
                    sharpness = cv2.Laplacian(face_crop, cv2.CV_64F).var()
                    
                    # Hiển thị thông tin
                    cv2.putText(frame, f"Sharpness: {int(sharpness)}", (left, top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    if sharpness >= SHARPNESS_THRESHOLD:
                        # Phát hiện landmark khuôn mặt
                        face_landmarks = face_recognition.face_landmarks(rgb_frame, face_locations)
                        
                        if face_landmarks:
                            # Tính EAR (Eye Aspect Ratio)
                            left_eye = np.array(face_landmarks[0]['left_eye'])
                            right_eye = np.array(face_landmarks[0]['right_eye'])
                            
                            # Vẽ landmarks mắt
                            for (x, y) in left_eye:
                                cv2.circle(frame, (x, y), 2, (0, 255, 255), -1)
                            for (x, y) in right_eye:
                                cv2.circle(frame, (x, y), 2, (0, 255, 255), -1)
                            
                            # Tính EAR cho cả hai mắt
                            left_ear = calculate_ear(left_eye)
                            right_ear = calculate_ear(right_eye)
                            ear = (left_ear + right_ear) / 2.0
                            
                            # Phát hiện chớp mắt
                            if ear < EAR_THRESHOLD:
                                self.eye_closed_frames += 1
                                self.eye_open_frames = 0
                                cv2.putText(frame, "BLINK", (right + 10, top + 30),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            else:
                                self.eye_open_frames += 1
                                # Nếu mắt được mở sau khi đóng, đếm như một lần chớp
                                if self.eye_closed_frames >= 2 and self.eye_open_frames > 3:
                                    self.blink_count += 1
                                    self.eye_closed_frames = 0
                    
                    # Lưu frame hiện tại để hiển thị
                    with threading.Lock():
                        self.current_frame = frame
                else:
                    # Không phát hiện khuôn mặt
                    cv2.putText(frame, "No face detected", (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    with threading.Lock():
                        self.current_frame = frame
                
                # Kiểm tra điều kiện nút Đăng ký
                if self.blink_count >= 3:
                    self.register_button.set_sensitive(True)
                
                time.sleep(0.01)  # Giảm CPU usage
                
        except Exception as e:
            GLib.idle_add(self.show_error_dialog, f"Lỗi xử lý camera: {str(e)}")
    
    def update_ui(self):
        if hasattr(self, 'current_frame'):
            with threading.Lock():
                frame = self.current_frame.copy()
            
            # Thêm thông tin blink count
            cv2.putText(frame, f"Blink count: {self.blink_count}/3", (50, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # Convert frame sang định dạng Pixbuf để hiển thị trong Gtk.Image
            height, width, channels = frame.shape
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(
                frame.tobytes(),
                GdkPixbuf.Colorspace.RGB,
                False,
                8,
                width,
                height,
                width * channels
            )
            self.camera_image.set_from_pixbuf(pixbuf)
            
            # Cập nhật trạng thái
            if self.blink_count >= 3:
                self.status_label.set_text("Đã đủ điều kiện đăng ký! Nhấn nút 'Đăng ký' để hoàn tất.")
            else:
                self.status_label.set_text(f"Đã phát hiện {self.blink_count}/3 lần chớp mắt. Tiếp tục...")
        
        return self.running
    
    def on_register_clicked(self, button):
        # Vô hiệu hóa nút đăng ký
        self.register_button.set_sensitive(False)
        self.status_label.set_text("Đang đăng ký khuôn mặt...")
        
        # Thực hiện đăng ký trong thread riêng để không chặn UI
        threading.Thread(target=self.register_face).start()
    
    def register_face(self):
        try:
            ret, frame = self.cap.read()
            if not ret:
                GLib.idle_add(self.show_error_dialog, "Không thể đọc frame từ camera!")
                return
            
            # Chuyển đổi màu
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Phát hiện khuôn mặt
            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                GLib.idle_add(self.show_error_dialog, "Không phát hiện được khuôn mặt!")
                return
            
            # Tạo encoding
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            if not face_encodings:
                GLib.idle_add(self.show_error_dialog, "Không thể tạo face encoding!")
                return
            
            # Lưu encoding
            result = save_face_encoding(self.username, face_encodings[0])
            
            if result:
                GLib.idle_add(self.show_success_dialog)
            else:
                GLib.idle_add(self.show_error_dialog, "Không thể lưu dữ liệu khuôn mặt!")
            
        except Exception as e:
            GLib.idle_add(self.show_error_dialog, f"Lỗi đăng ký: {str(e)}")
    
    def show_success_dialog(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Đăng ký thành công"
        )
        dialog.format_secondary_text(f"Đã đăng ký khuôn mặt cho người dùng {self.username}")
        dialog.run()
        dialog.destroy()
        self.running = False
        self.destroy()
    
    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Lỗi"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
        self.register_button.set_sensitive(True)
    
    def on_cancel_clicked(self, button):
        self.running = False
        self.destroy()
    
    def on_destroy(self, *args):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        Gtk.main_quit()

if __name__ == "__main__":
    ensure_data_dir()
    window = FaceRegistrationWindow()
    window.connect("destroy", window.on_destroy)
    window.show_all()
    Gtk.main()
