#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk, Pango, Gio
import os
import sys
import random
import time
import math
import cairo
import threading
import cv2
import numpy as np
import face_recognition
import json
from pathlib import Path
import logging

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/var/log/face-auth-gui.log'
)
logger = logging.getLogger('face-auth-gui')

class FaceAuthGUI(Gtk.Window):
    def __init__(self, username=None, result_path=None, lock_path=None):
        Gtk.Window.__init__(self, title="Face Authentication")
        self.set_size_request(340, 420)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        
        # Lưu đường dẫn file
        self.username = username if username else os.environ.get('USER')
        self.result_path = result_path
        self.lock_path = lock_path
        
        # Các ngưỡng xác thực
        self.EAR_THRESHOLD = 0.25
        self.REQUIRED_BLINKS = 2
        self.SHARPNESS_THRESHOLD = 50
        self.FACE_MATCH_THRESHOLD = 0.5
        
        # Setup giao diện đồ họa
        self.setup_gui()
        
        # Biến trạng thái xác thực
        self.blink_count = 0
        self.eye_closed_frames = 0
        self.eye_open_frames = 0
        self.face_verified = False
        self.face_encoding = self.load_face_encoding()
        
        # Biến đếm số lần thử
        self.attempt_count = 0
        self.max_attempts = 3
        
        # Khởi tạo luồng camera riêng biệt
        self.camera_thread = None
        self.cap = None
        self.running = True
        self.current_frame = None
        self.lock = threading.Lock()
        
        # Bắt đầu xác thực
        self.start_authentication()
        
    def setup_gui(self):
        """Thiết lập giao diện đồ họa"""
        # Loại bỏ viền và làm nền mờ
        self.set_app_paintable(True)
        self.set_decorated(False)
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        
        self.set_opacity(0.95)
        
        # Main container
        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(outer_box)
        
        # Overlay for main content
        overlay = Gtk.Overlay()
        outer_box.pack_start(overlay, True, True, 0)
        
        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        overlay.add(main_box)
        
        # Tiêu đề ở góc trên
        header_box = Gtk.Box(spacing=0)
        header_box.set_margin_bottom(12)
        main_box.pack_start(header_box, False, False, 0)
        
        title_label = Gtk.Label()
        title_label.set_markup("<span size='medium' font_weight='bold' alpha='80%'>Xác thực</span>")
        title_label.set_halign(Gtk.Align.START)
        header_box.pack_start(title_label, True, True, 0)
        
        close_button = Gtk.Button()
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_icon = Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        close_button.add(close_icon)
        close_button.connect("clicked", self.on_cancel_clicked)
        header_box.pack_end(close_button, False, False, 0)
        
        # Vùng animation chính
        self.animation_area = Gtk.DrawingArea()
        self.animation_area.set_size_request(300, 300)
        self.animation_area.set_hexpand(True)
        self.animation_area.set_vexpand(True)
        self.animation_area.connect("draw", self.on_draw_animation)
        main_box.pack_start(self.animation_area, True, True, 0)
        
        # Status message
        self.status_label = Gtk.Label()
        self.status_label.set_markup("<span size='medium' alpha='90%'>Đang chuẩn bị...</span>")
        self.status_label.set_justify(Gtk.Justification.CENTER)
        main_box.pack_start(self.status_label, False, False, 0)
        
        # Hiển thị số lần thử
        self.attempt_label = Gtk.Label()
        self.attempt_label.set_markup(f"<span size='small' alpha='70%'>Lần thử: 1/{self.max_attempts}</span>")
        self.attempt_label.set_justify(Gtk.Justification.CENTER)
        main_box.pack_start(self.attempt_label, False, False, 0)
        
        # Các nút điều khiển
        button_box = Gtk.Box(spacing=20)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(6)
        main_box.pack_end(button_box, False, False, 10)
        
        # Password button
        self.password_button = Gtk.Button()
        password_icon = Gtk.Image.new_from_icon_name("dialog-password-symbolic", Gtk.IconSize.BUTTON)
        self.password_button.add(password_icon)
        self.password_button.set_tooltip_text("Dùng mật khẩu")
        self.password_button.connect("clicked", self.on_cancel_clicked)
        self.password_button.get_style_context().add_class("circular")
        button_box.pack_start(self.password_button, False, False, 0)
        
        # Retry button
        self.retry_button = Gtk.Button()
        retry_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.retry_button.add(retry_icon)
        self.retry_button.set_tooltip_text("Thử lại")
        self.retry_button.connect("clicked", self.on_retry_clicked)
        self.retry_button.get_style_context().add_class("circular")
        self.retry_button.set_sensitive(False)  # Disabled initially
        button_box.pack_start(self.retry_button, False, False, 0)
        
        # Animation variables
        self.animation_state = "waiting"  # waiting, scanning, success, failure
        self.progress = 0
        self.success_progress = 0
        
        # Face animation variables
        self.face_y = 0
        self.face_rotation = 0
        self.face_scale = 1.0
        self.anim_variant = 0
        self.anim_time = 0
        
        # Success particles
        self.particles = []
        for _ in range(24):
            self.particles.append({
                'x': random.uniform(-1, 1),
                'y': random.uniform(-1, 1),
                'size': random.uniform(2.5, 7),
                'speed': random.uniform(0.5, 2.0),
                'delay': random.uniform(0, 15),
                'angle': random.uniform(0, math.pi*2)
            })
        
        # Animation timer
        GLib.timeout_add(16, self.update_animation)
        GLib.timeout_add(1000, self.switch_to_scanning)
        
        # Add CSS for styling
        self.apply_css()
        
        # Drag window support
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                        Gdk.EventMask.BUTTON_RELEASE_MASK | 
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("button-press-event", self.on_window_clicked)
        self.connect("button-release-event", self.on_window_release)
        self.connect("motion-notify-event", self.on_window_motion)
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.dragging = False
        
        # Thiết lập sự kiện đóng
        self.connect("destroy", self.on_window_destroy)
        
    def apply_css(self):
        """Áp dụng style CSS cho giao diện"""
        css_provider = Gtk.CssProvider()
        css = """
        window {
            background: linear-gradient(165deg, rgba(20, 23, 26, 0.96), rgba(18, 21, 24, 0.98));
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        label {
            color: white;
        }
        
        button {
            background-color: transparent;
            color: white;
            border: none;
            padding: 8px;
            min-height: 36px;
            min-width: 36px;
            transition: all 180ms ease;
        }
        
        button:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        
        button:active {
            background-color: rgba(255, 255, 255, 0.2);
        }
        
        button.circular {
            border-radius: 50%;
            padding: 8px;
        }
        """
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_draw_animation(self, widget, cr):
        """Vẽ animation tinh tế và tối giản"""
        # Kích thước widget
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        
        # Tọa độ tâm
        center_x = width / 2
        center_y = height / 2
        
        # Xóa nền
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        
        # Vẽ các thành phần dựa trên trạng thái
        if self.animation_state == "waiting":
            self.draw_waiting_state(cr, center_x, center_y)
        elif self.animation_state == "scanning":
            self.draw_scanning_state(cr, center_x, center_y)
        elif self.animation_state == "success":
            self.draw_success_state(cr, center_x, center_y)
        elif self.animation_state == "failure":
            self.draw_failure_state(cr, center_x, center_y)
        
        return True
    
    def draw_waiting_state(self, cr, cx, cy):
        """Vẽ trạng thái chờ - tối giản và thanh lịch"""
        radius = 60 + 3.5 * math.sin(time.time() * 1.5)
        
        # Vòng tròn mờ đầu tiên
        cr.set_source_rgba(0.3, 0.5, 0.8, 0.08)
        cr.arc(cx, cy, radius + 12, 0, 2 * math.pi)
        cr.fill()
        
        # Vòng tròn mờ thứ hai
        cr.set_source_rgba(0.3, 0.5, 0.8, 0.06)
        cr.arc(cx, cy, radius + 24, 0, 2 * math.pi)
        cr.fill()
        
        # Vẽ gradient radial
        pat = cairo.RadialGradient(cx, cy, 0, cx, cy, radius)
        pat.add_color_stop_rgba(0, 0.2, 0.4, 0.8, 0.03)
        pat.add_color_stop_rgba(0.8, 0.2, 0.4, 0.8, 0.06)
        pat.add_color_stop_rgba(1, 0.2, 0.4, 0.8, 0.12)
        cr.set_source(pat)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.fill()
        
        # Vẽ đường viền mỏng
        cr.set_source_rgba(0.4, 0.6, 0.9, 0.2)
        cr.set_line_width(1.5)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()
        
        # Vẽ các hạt nhỏ xoay quanh
        num_particles = 6
        particle_color = (0.4, 0.6, 0.9)
        
        for i in range(num_particles):
            angle = time.time() * (0.3 + 0.2 * i) % (2 * math.pi)
            distance = radius - 6 + 12 * math.sin(time.time() * 0.5 + i)
            
            x = cx + distance * math.cos(angle)
            y = cy + distance * math.sin(angle)
            
            particle_size = 2.5 + math.sin(time.time() * 2 + i)
            
            cr.set_source_rgba(*particle_color, 0.6)
            cr.arc(x, y, particle_size, 0, 2 * math.pi)
            cr.fill()
        
        # Vẽ khuôn mặt đơn giản ở giữa
        self.draw_minimal_face(cr, cx, cy, "waiting", 1.2)
    
    def draw_scanning_state(self, cr, cx, cy):
        """Vẽ trạng thái đang quét - tối giản và hiện đại"""
        radius = 60
        
        # Viền vòng tròn đầy đủ - mờ
        cr.set_source_rgba(0.3, 0.5, 0.8, 0.1)
        cr.set_line_width(2.5)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()
        
        # Phần tiến trình
        cr.set_source_rgba(0.3, 0.6, 0.9, 0.6)
        cr.set_line_width(2.5)
        cr.arc(cx, cy, radius, -math.pi/2, -math.pi/2 + (2 * math.pi * self.progress))
        cr.stroke()
        
        # Hiệu ứng quét
        scan_pos = cy + 24 * math.sin(self.progress * 2 * math.pi)
        scan_width = 50 + 24 * math.sin(self.progress * 4 * math.pi)
        
        scan_pat = cairo.LinearGradient(cx - scan_width/2, scan_pos, cx + scan_width/2, scan_pos)
        scan_pat.add_color_stop_rgba(0, 0.3, 0.6, 0.9, 0)
        scan_pat.add_color_stop_rgba(0.5, 0.3, 0.6, 0.9, 0.3)
        scan_pat.add_color_stop_rgba(1, 0.3, 0.6, 0.9, 0)
        
        cr.set_source(scan_pat)
        cr.rectangle(cx - scan_width/2, scan_pos - 1.5, scan_width, 3)
        cr.fill()
        
        # Vẽ khuôn mặt ở giữa
        self.draw_minimal_face(cr, cx, cy, "scanning", 1.2)
    
    def draw_success_state(self, cr, cx, cy):
        """Vẽ trạng thái thành công - tối giản và trang nhã"""
        radius = 60 + self.success_progress * 2
        
        # Vòng tròn hiệu ứng lan tỏa - mờ dần
        opacity = max(0, 0.3 - (self.success_progress / 50) * 0.3)
        cr.set_source_rgba(0.2, 0.8, 0.4, opacity)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.fill()
        
        # Vẽ các hạt bung ra
        for particle in self.particles:
            if particle['delay'] <= self.success_progress:
                # Tính toán vị trí hạt
                factor = min(1.0, (self.success_progress - particle['delay']) / 25)
                
                x = cx + particle['x'] * radius * 2.2 * factor
                y = cy + particle['y'] * radius * 2.2 * factor
                
                # Hiệu ứng mờ dần khi di chuyển ra xa
                opacity = max(0, 0.8 - factor * 0.8)
                
                # Vẽ hạt
                cr.set_source_rgba(0.2, 0.8, 0.4, opacity)
                cr.arc(x, y, particle['size'] * (1 - factor * 0.5), 0, 2 * math.pi)
                cr.fill()
        
        # Vẽ dấu tích - xuất hiện dần
        if self.success_progress > 10:
            tick_progress = min(1.0, (self.success_progress - 10) / 15)
            
            cr.set_source_rgba(0.2, 0.8, 0.4, 0.9)
            cr.set_line_width(3)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            
            # Vẽ nét đầu tiên của dấu tích
            if tick_progress > 0.3:
                first_tick = min(1.0, (tick_progress - 0.3) / 0.4)
                cr.move_to(cx - 18, cy)
                cr.line_to(cx - 18 + first_tick * 12, cy + first_tick * 12)
                cr.stroke()
            
            # Vẽ nét thứ hai của dấu tích
            if tick_progress > 0.6:
                second_tick = min(1.0, (tick_progress - 0.6) / 0.4)
                cr.move_to(cx - 6, cy + 12)
                cr.line_to(cx - 6 + second_tick * 24, cy + 12 - second_tick * 24)
                cr.stroke()
        
        # Vẽ khuôn mặt ở giữa
        self.draw_minimal_face(cr, cx, cy, "success", 1.2)
    
    def draw_failure_state(self, cr, cx, cy):
        """Vẽ trạng thái thất bại - tối giản và tinh tế"""
        base_radius = 60
        
        # Vòng tròn hiệu ứng lan tỏa - đỏ mờ
        radius = base_radius + self.progress * 12
        opacity = max(0, 0.3 - (self.progress / 1.0) * 0.3)
        cr.set_source_rgba(0.8, 0.2, 0.2, opacity)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.fill()
        
        # Viền vòng tròn mờ
        cr.set_source_rgba(0.8, 0.2, 0.2, 0.1)
        cr.set_line_width(2.5)
        cr.arc(cx, cy, base_radius, 0, 2 * math.pi)
        cr.stroke()
        
        # Hiệu ứng rung
        shake = math.sin(time.time() * 15) * 4 * max(0, 1 - self.progress)
        
        # Vẽ dấu X
        if self.progress > 0.2:
            x_progress = min(1.0, (self.progress - 0.2) / 0.5)
            
            cr.set_source_rgba(0.8, 0.2, 0.2, 0.7)
            cr.set_line_width(3)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            
            # Vẽ nét đầu tiên của X
            cr.move_to(cx - 15 + shake, cy - 15)
            cr.line_to(cx - 15 + x_progress * 30 + shake, cy - 15 + x_progress * 30)
            cr.stroke()
            
            # Vẽ nét thứ hai của X
            if x_progress > 0.6:
                second_x = min(1.0, (x_progress - 0.6) / 0.4)
                cr.move_to(cx + 15 + shake, cy - 15)
                cr.line_to(cx + 15 - second_x * 30 + shake, cy - 15 + second_x * 30)
                cr.stroke()
        
        # Vẽ khuôn mặt ở giữa
        self.draw_minimal_face(cr, cx, cy, "failure", 1.2)
    
    def draw_minimal_face(self, cr, cx, cy, state, size_factor=1.0):
        """Vẽ khuôn mặt tối giản"""
        face_size = 30 * self.face_scale * size_factor
        
        # Tọa độ đã biến đổi cho animation
        fx = cx
        fy = cy + self.face_y
        
        # Lưu trạng thái hiện tại
        cr.save()
        
        # Áp dụng xoay nếu cần
        if self.face_rotation != 0:
            cr.translate(cx, cy)
            cr.rotate(math.radians(self.face_rotation))
            cr.translate(-cx, -cy)
        
        # Vẽ khuôn mặt dựa trên trạng thái
        if state == "waiting":
            # Mặt trung tính - tối giản
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.7)
            
            # Mắt trái
            eye_open = (self.anim_time % 90) < 85  # Chớp mắt
            if eye_open:
                cr.set_line_width(1.8)
                cr.arc(fx - face_size/3, fy - face_size/6, 2, 0, 2 * math.pi)
                cr.fill()
            else:
                cr.set_line_width(1.8)
                cr.move_to(fx - face_size/3 - 3, fy - face_size/6)
                cr.line_to(fx - face_size/3 + 3, fy - face_size/6)
                cr.stroke()
            
            # Mắt phải
            if eye_open:
                cr.arc(fx + face_size/3, fy - face_size/6, 2, 0, 2 * math.pi)
                cr.fill()
            else:
                cr.move_to(fx + face_size/3 - 3, fy - face_size/6)
                cr.line_to(fx + face_size/3 + 3, fy - face_size/6)
                cr.stroke()
            
            # Miệng - đường thẳng đơn giản
            cr.set_line_width(1.8)
            cr.move_to(fx - face_size/4, fy + face_size/4)
            cr.line_to(fx + face_size/4, fy + face_size/4)
            cr.stroke()
            
        elif state == "scanning":
            # Mặt tò mò - tối giản
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.7)
            
            # Mắt trái - sáng hơn khi quét
            cr.set_line_width(1.8)
            cr.arc(fx - face_size/3, fy - face_size/6, 2.5, 0, 2 * math.pi)
            cr.fill()
            
            # Mắt phải
            cr.arc(fx + face_size/3, fy - face_size/6, 2.5, 0, 2 * math.pi)
            cr.fill()
            
            # Miệng - hơi mở
            mouth_factor = 0.1 + 0.04 * math.sin(time.time() * 3)
            cr.arc(fx, fy + face_size/4, face_size * mouth_factor, 0, math.pi)
            cr.fill()
            
        elif state == "success":
            # Mặt vui - tối giản
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.7)
            
            # Mắt trái - cong lên khi vui
            cr.set_line_width(1.8)
            cr.arc(fx - face_size/3, fy - face_size/6, 1.2, 0, math.pi)
            cr.stroke()
            
            # Mắt phải
            cr.arc(fx + face_size/3, fy - face_size/6, 1.2, 0, math.pi)
            cr.stroke()
            
            # Miệng cười
            cr.set_line_width(1.8)
            cr.arc(fx, fy + face_size/8, face_size/3, 0, math.pi)
            cr.stroke()
            
        elif state == "failure":
            # Mặt buồn - tối giản
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.7)
            
            # Mắt trái - buồn
            cr.set_line_width(1.8)
            cr.move_to(fx - face_size/3 - 3, fy - face_size/6)
            cr.line_to(fx - face_size/3 + 3, fy - face_size/6)
            cr.stroke()
            
            # Mắt phải
            cr.move_to(fx + face_size/3 - 3, fy - face_size/6)
            cr.line_to(fx + face_size/3 + 3, fy - face_size/6)
            cr.stroke()
            
            # Miệng buồn
            cr.set_line_width(1.8)
            cr.arc(fx, fy + face_size/2, face_size/3, math.pi, 2 * math.pi)
            cr.stroke()
            
        # Khôi phục trạng thái
        cr.restore()

    def update_animation(self):
        """Cập nhật các tham số animation"""
        # Đếm thời gian
        self.anim_time += 1
        
        if self.animation_state == "waiting":
            # Chu kỳ animation chờ
            if self.anim_time >= 180:
                self.anim_time = 0
                self.anim_variant = (self.anim_variant + 1) % 3
            
            # Các biến thể animation khi chờ
            if self.anim_variant == 0:
                # Gật đầu nhẹ
                self.face_y = 3.5 * math.sin(time.time() * 1.5)
                self.face_rotation = 0
                self.face_scale = 1.0
            elif self.anim_variant == 1:
                # Nghiêng đầu
                self.face_y = 0
                self.face_rotation = 10 * math.sin(time.time())
                self.face_scale = 1.0
            else:
                # Thở (phóng to thu nhỏ)
                self.face_y = 0
                self.face_rotation = 0
                self.face_scale = 1.0 + 0.1 * math.sin(time.time() * 1.5)
            
        elif self.animation_state == "scanning":
            # Tiến trình quét
            self.progress = (self.progress + 0.008) % 1.0
            
            # Chuyển động nhẹ khi quét
            self.face_y = 2.5 * math.sin(time.time() * 3)
            self.face_rotation = 4 * math.sin(time.time() * 1.5)
            self.face_scale = 1.0 + 0.07 * math.sin(time.time() * 2)
            
            # Cập nhật nhãn trạng thái từ kết quả xử lý khuôn mặt
            if self.blink_count > 0:
                self.status_label.set_markup(f"<span size='medium' alpha='90%'>Đã phát hiện {self.blink_count} lần chớp mắt</span>")
            
            # Kiểm tra điều kiện chuyển trạng thái
            if self.blink_count >= self.REQUIRED_BLINKS and self.face_verified:
                self.animation_state = "success"
                self.success_progress = 0
                self.status_label.set_markup("<span size='medium' foreground='#22cc66'>Xác thực thành công</span>")
                GLib.timeout_add(1500, self.authentication_success)
            
        elif self.animation_state == "success":
            # Tiến trình thành công
            if self.success_progress < 30:
                self.success_progress += 1
            
            # Chuyển động vui vẻ
            if self.success_progress < 15:
                bounce = min(1.0, self.success_progress / 8)
                self.face_y = -6 * bounce * math.sin(time.time() * 8)
                self.face_rotation = 6 * bounce * math.sin(time.time() * 6)
                self.face_scale = 1.0 + 0.18 * bounce * math.sin(time.time() * 5)
            else:
                self.face_y = -4 + 1.5 * math.sin(time.time() * 3)
                self.face_rotation = 0
                self.face_scale = 1.0 + 0.1 * math.sin(time.time() * 2)
            
        elif self.animation_state == "failure":
            # Tiến trình thất bại
            if self.progress < 1.0:
                self.progress += 0.015
            
            # Rung lắc khi thất bại
            shake = 4 * max(0, 1 - self.progress)
            self.face_y = 4 + shake * math.sin(time.time() * 12)
            self.face_rotation = shake * 3 * math.sin(time.time() * 15)
            self.face_scale = 1.0 - 0.05 * math.sin(time.time() * 6)
        
        # Cập nhật vẽ lại animation
        self.animation_area.queue_draw()
        return True
    
    def switch_to_scanning(self):
        """Bắt đầu quét"""
        if self.animation_state == "waiting":
            self.animation_state = "scanning"
            self.progress = 0
            self.status_label.set_markup("<span size='medium' alpha='90%'>Đang nhận diện...</span>")
        return False
    
    def authentication_success(self):
        """Xử lý khi xác thực thành công"""
        # Ghi kết quả ra file
        if self.result_path:
            with open(self.result_path, 'w') as f:
                f.write("SUCCESS")
        
        # Xóa lock file (nếu có)
        if self.lock_path and os.path.exists(self.lock_path):
            try:
                os.unlink(self.lock_path)
            except:
                pass
        
        # Đóng cửa sổ sau một chút delay để hiển thị hoàn tất animation
        GLib.timeout_add(500, self.destroy)
        return False
    
    def authentication_failure(self, reason="Không thể xác thực"):
        """Xử lý khi xác thực thất bại"""
        self.animation_state = "failure"
        self.progress = 0
        self.status_label.set_markup(f"<span size='medium' foreground='#ff5566'>{reason}</span>")
        self.retry_button.set_sensitive(True)
        
        # Cập nhật số lần thử
        self.attempt_count += 1
        
        # Hiển thị số lần thử
        if self.attempt_count < self.max_attempts:
            self.attempt_label.set_markup(f"<span size='small' alpha='70%'>Lần thử: {self.attempt_count+1}/{self.max_attempts}</span>")
        else:
            # Đã hết số lần thử
            self.attempt_label.set_markup("<span size='small' foreground='#ff5566'>Đã hết số lần thử</span>")
            
            # Ghi kết quả ra file
            if self.result_path:
                with open(self.result_path, 'w') as f:
                    f.write("MAX_ATTEMPTS_REACHED")
            
            # Xóa lock file sau một lúc
            GLib.timeout_add(2000, self.remove_lock_file)
        
        return False
    
    def remove_lock_file(self):
        """Xóa lock file"""
        if self.lock_path and os.path.exists(self.lock_path):
            try:
                os.unlink(self.lock_path)
            except:
                pass
        return False
    
    def on_retry_clicked(self, button):
        """Xử lý khi người dùng nhấn nút thử lại"""
        if self.attempt_count < self.max_attempts:
            # Reset trạng thái xác thực
            self.blink_count = 0
            self.eye_closed_frames = 0
            self.eye_open_frames = 0
            self.face_verified = False
            
            # Chuyển về trạng thái quét lại
            self.animation_state = "scanning"
            self.progress = 0
            self.status_label.set_markup("<span size='medium' alpha='90%'>Đang nhận diện...</span>")
            
            # Vô hiệu hóa nút thử lại
            self.retry_button.set_sensitive(False)
        else:
            # Đã hết lượt thử -> chuyển sang xác thực mật khẩu
            self.on_cancel_clicked(button)
    
    def on_cancel_clicked(self, button):
        """Xử lý khi người dùng nhấn nút hủy"""
        # Ghi kết quả ra file
        if self.result_path:
            with open(self.result_path, 'w') as f:
                f.write("CANCEL")
        
        # Xóa lock file
        self.remove_lock_file()
        
        # Đóng cửa sổ
        self.destroy()
    
    def on_window_clicked(self, widget, event):
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        return True
        
    def on_window_release(self, widget, event):
        self.dragging = False
        return True
        
    def on_window_motion(self, widget, event):
        if self.dragging:
            window_x, window_y = self.get_position()
            new_x = window_x + event.x - self.drag_start_x
            new_y = window_y + event.y - self.drag_start_y
            self.move(int(new_x), int(new_y))
        return True
    
    def start_authentication(self):
        """Khởi động luồng xác thực khuôn mặt"""
        self.camera_thread = threading.Thread(target=self.authentication_thread)
        self.camera_thread.daemon = True
        self.camera_thread.start()
    
    def authentication_thread(self):
        """Luồng xử lý xác thực khuôn mặt"""
        try:
            # Mở camera
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            if not self.cap.isOpened():
                GLib.idle_add(self.authentication_failure, "Không thể mở camera")
                return
            
            # Chuẩn bị các biến
            blink_count = 0
            eye_closed_frames = 0
            eye_open_frames = 0
            start_time = time.time()
            
            # Vòng lặp xử lý từng frame
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                
                # Xử lý frame
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Phát hiện khuôn mặt
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if not face_locations:
                    continue
                
                # Kiểm tra độ sắc nét
                top, right, bottom, left = face_locations[0]
                face_crop = gray[top:bottom, left:right]
                sharpness = cv2.Laplacian(face_crop, cv2.CV_64F).var()
                
                if sharpness < self.SHARPNESS_THRESHOLD:
                    # Hình ảnh quá mờ, có thể là ảnh in
                    continue
                
                # Phát hiện landmark khuôn mặt
                face_landmarks = face_recognition.face_landmarks(rgb_frame, face_locations)
                
                if face_landmarks:
                    # Tính EAR (Eye Aspect Ratio)
                    left_eye = np.array(face_landmarks[0]['left_eye'])
                    right_eye = np.array(face_landmarks[0]['right_eye'])
                    
                    # Tính EAR cho cả hai mắt
                    left_ear = self.calculate_ear(left_eye)
                    right_ear = self.calculate_ear(right_eye)
                    ear = (left_ear + right_ear) / 2.0
                    
                    # Phát hiện chớp mắt
                    if ear < self.EAR_THRESHOLD:
                        eye_closed_frames += 1
                        eye_open_frames = 0
                    else:
                        eye_open_frames += 1
                        # Nếu mắt được mở sau khi đóng, đếm như một lần chớp
                        if eye_closed_frames >= 2 and eye_open_frames > 3:
                            blink_count += 1
                            eye_closed_frames = 0
                            # Cập nhật số lần chớp mắt (từ thread chính)
                            self.blink_count = blink_count
                
                # Mã hóa và so sánh khuôn mặt (không làm mỗi frame để tiết kiệm tài nguyên)
                if len(face_locations) > 0 and self.face_encoding is not None:
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    
                    if face_encodings:
                        current_encoding = face_encodings[0]
                        # Tính khoảng cách Euclidean
                        distance = np.linalg.norm(current_encoding - self.face_encoding)
                        
                        # Cập nhật trạng thái xác thực
                        if distance < self.FACE_MATCH_THRESHOLD:
                            self.face_verified = True
                        else:
                            # Nếu khuôn mặt không khớp sau nhiều lần thử
                            verification_time = time.time() - start_time
                            if verification_time > 5 and not self.face_verified:
                                GLib.idle_add(self.authentication_failure, "Khuôn mặt không khớp")
                                break
                
                # Kiểm tra điều kiện kết thúc
                verification_time = time.time() - start_time
                
                # Timeout nếu quá lâu
                if verification_time > 15:
                    GLib.idle_add(self.authentication_failure, "Hết thời gian xác thực")
                    break
            
        except Exception as e:
            logger.error(f"Camera thread error: {str(e)}")
            GLib.idle_add(self.authentication_failure, f"Lỗi: {str(e)}")
        finally:
            # Đảm bảo giải phóng camera
            if self.cap:
                self.cap.release()
    
    def calculate_ear(self, eye):
        """Tính tỷ lệ khía cạnh mắt (EAR)"""
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        return (A + B) / (2.0 * C)
    
    def load_face_encoding(self):
        """Tải face encoding của người dùng"""
        try:
            data_dir = Path.home() / '.face-auth'
            encoding_file = data_dir / f"{self.username}.json"
            
            if not encoding_file.exists():
                GLib.idle_add(self.authentication_failure, "Người dùng chưa đăng ký khuôn mặt")
                return None
                
            with open(encoding_file, 'r') as f:
                data = json.load(f)
            return np.array(data["encoding"])
        except Exception as e:
            logger.error(f"Error loading face encoding: {str(e)}")
            GLib.idle_add(self.authentication_failure, "Không thể tải thông tin khuôn mặt")
            return None
    
    def on_window_destroy(self, widget):
        """Xử lý khi cửa sổ đóng"""
        self.running = False
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(1.0)  # Chờ thread camera kết thúc
        
        # Đảm bảo giải phóng camera
        if self.cap:
            self.cap.release()
        
        # Đảm bảo xóa lock file
        self.remove_lock_file()


if __name__ == "__main__":
    # Lấy thông số dòng lệnh
    username = sys.argv[1] if len(sys.argv) > 1 else None
    result_path = sys.argv[2] if len(sys.argv) > 2 else None
    lock_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Tạo lock file nếu được chỉ định
    if lock_path:
        with open(lock_path, 'w') as f:
            f.write("RUNNING")
    
    # Khởi tạo và hiển thị giao diện
    win = FaceAuthGUI(username, result_path, lock_path)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
