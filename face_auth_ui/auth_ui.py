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
from face_auth.authenticator import FaceAuthenticator

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

class FaceAuthUI:
    def __init__(self, username):
        self.username = username
        self.animation_step = 0
        self.authentication_complete = False
        self.authentication_success = False
        self.frame_data = None
        self.callback = UICallback(self)
        
        # Khởi tạo cửa sổ GTK
        self.window = Gtk.Window(title="Face Authentication")
        self.window.set_default_size(500, 600)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_decorated(False)  # Không có viền, thanh tiêu đề
        self.window.set_app_paintable(True)
        
        # Tạo CSS
        self.setup_css()
        
        # Tạo layout
        self.build_ui()
        
        # Kết nối sự kiện
        self.window.connect("destroy", Gtk.main_quit)
        self.window.connect("draw", self.on_draw)
        
        # Cho phép bấm Escape để thoát
        self.window.connect("key-press-event", self.on_key_press)
        
        # Hiển thị các widget
        self.window.show_all()
        
        # Bắt đầu animation
        GLib.timeout_add(50, self.update_animation)
        
        # Khởi động thread xác thực
        threading.Thread(target=self.authenticate, daemon=True).start()
    
    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window {
                background-color: rgba(0, 0, 0, 0.85);
                border-radius: 10px;
            }
            label {
                font-size: 18px;
                font-weight: bold;
                color: white;
                margin: 10px;
            }
            .username {
                font-size: 24px;
                font-weight: bold;
                color: white;
                margin: 15px;
            }
            .status {
                font-size: 16px;
                color: #cccccc;
            }
        """)
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    
    def build_ui(self):
        # Container chính
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(30)
        box.set_margin_bottom(30)
        box.set_margin_start(30)
        box.set_margin_end(30)
        self.window.add(box)
        
        # Logo hoặc hình ảnh (tùy chọn)
        # logo = Gtk.Image.new_from_file("/path/to/logo.png")
        # box.pack_start(logo, False, False, 10)
        
        # Tên người dùng
        user_label = Gtk.Label(label=self.username)
        user_label.get_style_context().add_class("username")
        box.pack_start(user_label, False, False, 10)
        
        # Khu vực hiển thị animation
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(300, 300)
        self.drawing_area.connect("draw", self.draw_animation)
        box.pack_start(self.drawing_area, True, True, 10)
        
        # Khu vực hiển thị camera (tùy chọn)
        self.camera_area = Gtk.DrawingArea()
        self.camera_area.set_size_request(200, 150)
        self.camera_area.connect("draw", self.draw_camera_preview)
        box.pack_start(self.camera_area, False, False, 10)
        
        # Nhãn trạng thái
        self.status_label = Gtk.Label(label="Đang khởi động xác thực...")
        self.status_label.get_style_context().add_class("status")
        box.pack_start(self.status_label, False, False, 10)
    
    def authenticate(self):
        """Thực hiện xác thực trong thread riêng"""
        authenticator = FaceAuthenticator(self.username, self.callback)
        result = authenticator.authenticate()
        
        # Khi xác thực hoàn tất, cập nhật trạng thái
        self.authentication_complete = True
        self.authentication_success = result
        
        # Đặt hẹn giờ thoát
        if result:
            GLib.timeout_add(2000, self.exit_with_success)
        else:
            GLib.timeout_add(3000, self.exit_with_failure)
    
    def update_status(self, status, message):
        """Cập nhật trạng thái hiển thị"""
        self.status_label.set_text(message)
        
        if status == "success":
            self.authentication_complete = True
            self.authentication_success = True
        elif status == "fail" or status == "error":
            self.authentication_complete = True
            self.authentication_success = False
    
    def update_frame_display(self):
        """Cập nhật hiển thị camera"""
        if hasattr(self.callback, 'current_frame') and self.callback.current_frame is not None:
            self.frame_data = self.callback.current_frame
            self.camera_area.queue_draw()
    
    def draw_camera_preview(self, widget, cr):
        """Vẽ hình ảnh từ camera"""
        if self.frame_data is None:
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
    
    def draw_animation(self, widget, cr):
        """Vẽ animation xác thực"""
        # Lấy kích thước widget
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 3
        
        # Vẽ hình nền tròn
        cr.set_source_rgba(0.1, 0.1, 0.1, 0.5)
        cr.arc(center_x, center_y, radius + 5, 0, 2 * np.pi)
        cr.fill()
        
        if not self.authentication_complete:
            # Animation đang xác thực
            # Vẽ vòng tròn xanh quay
            angle_start = (self.animation_step % 100) / 100.0 * 2 * np.pi
            angle_end = angle_start + 0.8 * np.pi
            
            cr.set_source_rgba(0, 0.47, 0.84, 0.8)  # Màu xanh Microsoft
            cr.set_line_width(5)
            cr.arc(center_x, center_y, radius, angle_start, angle_end)
            cr.stroke()
            
            # Vẽ vòng tròn trắng đứng yên
            cr.set_source_rgba(0.8, 0.8, 0.8, 0.3)
            cr.set_line_width(2)
            cr.arc(center_x, center_y, radius, 0, 2 * np.pi)
            cr.stroke()
            
        elif self.authentication_success:
            # Hiệu ứng xác thực thành công
            # Vẽ vòng tròn xanh lá
            cr.set_source_rgba(0.06, 0.54, 0.24, 0.9)  # Màu xanh lá
            cr.set_line_width(5)
            cr.arc(center_x, center_y, radius, 0, 2 * np.pi)
            cr.stroke()
            
            # Vẽ dấu tích
            cr.set_source_rgba(0.06, 0.54, 0.24, 0.9)
            cr.set_line_width(7)
            cr.move_to(center_x - radius/2, center_y)
            cr.line_to(center_x - radius/6, center_y + radius/2)
            cr.line_to(center_x + radius/2, center_y - radius/3)
            cr.stroke()
            
        else:
            # Hiệu ứng xác thực thất bại
            # Vẽ vòng tròn đỏ
            cr.set_source_rgba(0.91, 0.07, 0.14, 0.9)  # Màu đỏ
            cr.set_line_width(5)
            cr.arc(center_x, center_y, radius, 0, 2 * np.pi)
            cr.stroke()
            
            # Vẽ dấu X
            cr.set_source_rgba(0.91, 0.07, 0.14, 0.9)
            cr.set_line_width(7)
            cr.move_to(center_x - radius/2, center_y - radius/2)
            cr.line_to(center_x + radius/2, center_y + radius/2)
            cr.stroke()
            
            cr.move_to(center_x + radius/2, center_y - radius/2)
            cr.line_to(center_x - radius/2, center_y + radius/2)
            cr.stroke()
    
    def update_animation(self):
        """Cập nhật animation"""
        if not self.authentication_complete:
            self.animation_step += 1
            self.drawing_area.queue_draw()
            return True  # Tiếp tục cập nhật
        else:
            self.drawing_area.queue_draw()
            return False  # Dừng cập nhật
    
    def on_draw(self, widget, cr):
        """Vẽ cửa sổ có bo góc"""
        allocation = widget.get_allocation()
        width = allocation.width
        height = allocation.height
        
        # Tạo cửa sổ trong suốt
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        
        # Vẽ nền với bo góc
        radius = 15
        degrees = np.pi / 180.0
        
        cr.new_sub_path()
        cr.arc(width - radius, radius, radius, -90 * degrees, 0 * degrees)
        cr.arc(width - radius, height - radius, radius, 0 * degrees, 90 * degrees)
        cr.arc(radius, height - radius, radius, 90 * degrees, 180 * degrees)
        cr.arc(radius, radius, radius, 180 * degrees, 270 * degrees)
        cr.close_path()
        
        cr.set_source_rgba(0, 0, 0, 0.85)
        cr.fill_preserve()
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        
        # Không bị clipping
        cr.set_operator(cairo.OPERATOR_OVER)
        
        return False
    
    def on_key_press(self, widget, event):
        """Xử lý phím bấm"""
        keyval = event.keyval
        keyname = Gdk.keyval_name(keyval)
        
        if keyname == 'Escape':
            self.exit_with_failure()
            return True
        
        return False
    
    def exit_with_success(self):
        """Thoát với trạng thái thành công"""
        Gtk.main_quit()
        sys.exit(0)
    
    def exit_with_failure(self):
        """Thoát với trạng thái thất bại"""
        Gtk.main_quit()
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: auth_ui.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    app = FaceAuthUI(username)
    Gtk.main()

if __name__ == "__main__":
    main()
