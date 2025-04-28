#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf
import cairo
import sys
import os
import threading
import time
import numpy as np
import cv2

# Import từ module face-auth
sys.path.append('/usr/lib/face-auth')
from face_auth.register import FaceRegistrar

class UICallback:
    def __init__(self, ui):
        self.ui = ui
        self.current_frame = None
    
    def __call__(self, status, message):
        GLib.idle_add(self.ui.update_status, status, message)
    
    def update_frame(self, frame):
        # Lưu frame hiện tại để hiển thị
        if frame is not None:
            self.current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            GLib.idle_add(self.ui.update_frame_display)

class FaceRegisterUI:
    def __init__(self, username):
        self.username = username
        self.animation_step = 0
        self.registration_complete = False
        self.registration_success = False
        self.frame_data = None
        self.callback = UICallback(self)
        
        # Khởi tạo cửa sổ GTK
        self.window = Gtk.Window(title="Face ID Registration")
        self.window.set_default_size(600, 700)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.connect("destroy", Gtk.main_quit)
        
        # Tạo CSS
        self.setup_css()
        
        # Tạo layout
        self.build_ui()
        
        # Hiển thị các widget
        self.window.show_all()
        
        # Bắt đầu animation
        GLib.timeout_add(50, self.update_animation)
    
    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window {
                background-color: #f0f0f0;
            }
            .title {
                font-size: 24px;
                font-weight: bold;
                color: #0078D4;
                margin: 15px;
            }
            .username {
                font-size: 18px;
                font-weight: bold;
                margin: 10px;
            }
            .instruction {
                font-size: 16px;
                margin: 5px;
            }
            .status {
                font-size: 16px;
                color: #333333;
                margin: 5px;
            }
            button {
                background-color: #0078D4;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                margin: 10px;
            }
            button:hover {
                background-color: #106EBE;
            }
            .success {
                color: #107C10;
                font-weight: bold;
            }
            .error {
                color: #E81123;
                font-weight: bold;
            }
        """)
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    
    def build_ui(self):
        # Container chính
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        self.window.add(main_box)
        
        # Tiêu đề
        title_label = Gtk.Label(label="Đăng ký Face ID")
        title_label.get_style_context().add_class("title")
        main_box.pack_start(title_label, False, False, 10)
        
        # Tên người dùng
        user_label = Gtk.Label(label=f"Người dùng: {self.username}")
        user_label.get_style_context().add_class("username")
        main_box.pack_start(user_label, False, False, 10)
        
        # Hướng dẫn
        instruction_label = Gtk.Label(
            label="Nhìn thẳng vào camera và chớp mắt 3 lần để xác nhận đó là bạn.\n"
                 "Giữ khuôn mặt của bạn trong khung hình và đảm bảo ánh sáng tốt."
        )
        instruction_label.get_style_context().add_class("instruction")
        main_box.pack_start(instruction_label, False, False, 10)
        
        # Khu vực hiển thị camera
        self.camera_area = Gtk.DrawingArea()
        self.camera_area.set_size_request(400, 300)
        self.camera_area.connect("draw", self.draw_camera_preview)
        main_box.pack_start(self.camera_area, True, True, 10)
        
        # Khu vực animation
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(200, 100)
        self.drawing_area.connect("draw", self.draw_animation)
        main_box.pack_start(self.drawing_area, False, False, 10)
        
        # Nhãn trạng thái
        self.status_label = Gtk.Label(label="Sẵn sàng đăng ký Face ID")
        self.status_label.get_style_context().add_class("status")
        main_box.pack_start(self.status_label, False, False, 10)
        
        # Nút điều khiển
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        
        self.start_button = Gtk.Button(label="Bắt đầu")
        self.start_button.connect("clicked", self.on_start_clicked)
        button_box.pack_start(self.start_button, False, False, 10)
        
        self.cancel_button = Gtk.Button(label="Hủy")
        self.cancel_button.connect("clicked", self.on_cancel_clicked)
        button_box.pack_start(self.cancel_button, False, False, 10)
        
        main_box.pack_start(button_box, False, False, 10)
    
    def on_start_clicked(self, button):
        self.start_button.set_sensitive(False)
        self.status_label.set_text("Đang khởi động camera...")
        threading.Thread(target=self.register_face, daemon=True).start()
    
    def on_cancel_clicked(self, button):
        Gtk.main_quit()
    
    def register_face(self):
        """Thực hiện đăng ký khuôn mặt trong thread riêng"""
        registrar = FaceRegistrar(self.username, self.callback)
        result = registrar.register()
        
        # Khi đăng ký hoàn tất, cập nhật trạng thái
        self.registration_complete = True
        self.registration_success = result
        
        # Cập nhật UI
        if result:
            GLib.idle_add(self.show_success)
        else:
            GLib.idle_add(self.show_failure)
    
    def show_success(self):
        self.status_label.set_text("Đăng ký thành công!")
        self.status_label.get_style_context().add_class("success")
        self.start_button.set_label("Đóng")
        self.start_button.set_sensitive(True)
        self.start_button.connect("clicked", lambda x: Gtk.main_quit())
        self.cancel_button.set_sensitive(False)
    
    def show_failure(self):
        self.status_label.set_text("Đăng ký thất bại. Vui lòng thử lại.")
        self.status_label.get_style_context().add_class("error")
        self.start_button.set_label("Thử lại")
        self.start_button.set_sensitive(True)
        self.start_button.connect("clicked", self.on_start_clicked)
    
    def update_status(self, status, message):
        """Cập nhật trạng thái hiển thị"""
        self.status_label.set_text(message)
        
        if status == "success":
            self.registration_complete = True
            self.registration_success = True
        elif status == "error" or status == "cancelled":
            self.registration_complete = True
            self.registration_success = False
    
    def update_frame_display(self):
        """Cập nhật hiển thị camera"""
        if hasattr(self.callback, 'current_frame') and self.callback.current_frame is not None:
            self.frame_data = self.callback.current_frame
            self.camera_area.queue_draw()
    
    def draw_camera_preview(self, widget, cr):
        """Vẽ hình ảnh từ camera"""
        if self.frame_data is None:
            # Vẽ khung rỗng
            allocation = widget.get_allocation()
            width = allocation.width
            height = allocation.height
            
            # Vẽ khung
            cr.set_source_rgb(0.2, 0.2, 0.2)
            cr.rectangle(0, 0, width, height)
            cr.fill()
            
            # Vẽ biểu tượng camera
            cr.set_source_rgb(0.6, 0.6, 0.6)
            cr.move_to(width/2 - 30, height/2 - 20)
            cr.line_to(width/2 + 30, height/2 - 20)
            cr.line_to(width/2 + 30, height/2 + 20)
            cr.line_to(width/2 - 30, height/2 + 20)
            cr.close_path()
            cr.fill()
            
            return
        
        # Lấy kích thước widget
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        
        # Chuyển numpy array thành pixbuf
        height_frame, width_frame, channels = self.frame_data.shape
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            self.frame_data.tobytes(),
            GdkPixbuf.Colorspace.RGB,
            False,
            8,
            width_frame,
            height_frame,
            width_frame * channels
        )
        
        # Scale pixbuf để phù hợp với widget
        scaled_pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
        
        # Vẽ pixbuf lên widget
        Gdk.cairo_set_source_pixbuf(cr, scaled_pixbuf, 0, 0)
        cr.paint()
        
        # Vẽ khung hướng dẫn khuôn mặt
        cr.set_source_rgba(0.0, 0.47, 0.84, 0.5)  # Màu xanh Microsoft, mờ
        cr.set_line_width(3)
        
        # Vẽ hình elip bao quanh khuôn mặt
        center_x = width / 2
        center_y = height / 2
        radius_x = width / 3
        radius_y = height / 2.5
        
        cr.save()
        cr.translate(center_x, center_y)
        cr.scale(radius_x, radius_y)
        cr.arc(0, 0, 1, 0, 2*np.pi)
        cr.restore()
        cr.stroke()
    
    def draw_animation(self, widget, cr):
        """Vẽ animation đăng ký"""
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        
        # Xóa background
        cr.set_source_rgb(0.9, 0.9, 0.9)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        
        # Lấy vị trí trung tâm
        center_x = width / 2
        
        # Vẽ thanh tiến trình
        bar_width = width * 0.8
        bar_height = 10
        bar_x = center_x - bar_width / 2
        bar_y = height / 2 - bar_height / 2
        
        # Vẽ nền thanh tiến trình
        cr.set_source_rgb(0.7, 0.7, 0.7)
        cr.rectangle(bar_x, bar_y, bar_width, bar_height)
        cr.fill()
        
        if not self.registration_complete:
            # Vẽ phần đã hoàn thành
            progress = (self.animation_step % 100) / 100.0
            cr.set_source_rgb(0.0, 0.47, 0.84)  # Màu xanh Microsoft
            cr.rectangle(bar_x, bar_y, bar_width * progress, bar_height)
            cr.fill()
        elif self.registration_success:
            # Hoàn thành thành công
            cr.set_source_rgb(0.06, 0.54, 0.24)  # Màu xanh lá
            cr.rectangle(bar_x, bar_y, bar_width, bar_height)
            cr.fill()
        else:
            # Hoàn thành thất bại
            cr.set_source_rgb(0.91, 0.07, 0.14)  # Màu đỏ
            cr.rectangle(bar_x, bar_y, bar_width, bar_height)
            cr.fill()
    
    def update_animation(self):
        """Cập nhật animation"""
        self.animation_step += 1
        self.drawing_area.queue_draw()
        return True  # Tiếp tục cập nhật

def main():
    if len(sys.argv) < 2:
        print("Usage: register_ui.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    app = FaceRegisterUI(username)
    Gtk.main()

if __name__ == "__main__":
    main()
