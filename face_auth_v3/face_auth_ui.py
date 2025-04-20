#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf, GLib
import cv2
import numpy as np
import sys
import threading
import time
import os

# The actual authentication happens via the CLI tool that this UI wraps
from face_auth_cli import authenticate_user

class FaceAuthWindow(Gtk.Window):
    def __init__(self, username):
        Gtk.Window.__init__(self, title="Face Authentication")
        self.username = username
        
        # Set window properties
        self.set_default_size(400, 450)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_decorated(False)  # Remove window decorations
        
        # Make window look nice
        self.set_app_paintable(True)
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        
        # Main container
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.set_margin_top(20)
        self.box.set_margin_bottom(20)
        self.box.set_margin_start(20)
        self.box.set_margin_end(20)
        self.add(self.box)
        
        # Header
        header_label = Gtk.Label()
        header_label.set_markup("<span size='large' weight='bold'>Face Authentication</span>")
        self.box.pack_start(header_label, False, False, 10)
        
        # Username display
        self.user_label = Gtk.Label()
        self.user_label.set_markup(f"<span>Authenticating: {self.username}</span>")
        self.box.pack_start(self.user_label, False, False, 5)
        
        # Camera feed
        self.camera_frame = Gtk.Frame()
        self.camera_frame.set_shadow_type(Gtk.ShadowType.NONE)
        self.image = Gtk.Image()
        self.camera_frame.add(self.image)
        self.box.pack_start(self.camera_frame, True, True, 0)
        
        # Status message
        self.status_label = Gtk.Label("Looking for your face...")
        self.box.pack_start(self.status_label, False, False, 5)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.box.pack_start(self.progress_bar, False, False, 5)
        
        # Button area
        button_box = Gtk.Box(spacing=10)
        self.box.pack_start(button_box, False, False, 5)
        
        # Try again button (initially hidden)
        self.retry_button = Gtk.Button(label="Try Again")
        self.retry_button.connect("clicked", self.on_retry_clicked)
        button_box.pack_start(self.retry_button, True, True, 0)
        self.retry_button.set_no_show_all(True)
        
        # Password button
        self.password_button = Gtk.Button(label="Use Password")
        self.password_button.connect("clicked", self.on_password_clicked)
        button_box.pack_start(self.password_button, True, True, 0)
        
        # Show everything
        self.show_all()
        self.retry_button.hide()
        
        # Initialize authentication
        self.authentication_thread = None
        self.cap = None
        self.stop_capture = threading.Event()
        self.face_verified = False
        self.auth_completed = False
        
        # Start camera capture
        self.start_camera()
        
        # Start authentication in a separate thread
        self.start_authentication()
    
    def start_camera(self):
        """Start the camera capture thread"""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.status_label.set_text("Error: Cannot access camera")
            return
            
        def update_camera():
            while not self.stop_capture.is_set():
                ret, frame = self.cap.read()
                if not ret:
                    continue
                    
                # Convert to GdkPixbuf
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (320, 240))
                pb = GdkPixbuf.Pixbuf.new_from_data(
                    frame.tobytes(),
                    GdkPixbuf.Colorspace.RGB,
                    False,
                    8,
                    frame.shape[1],
                    frame.shape[0],
                    frame.shape[1] * 3
                )
                
                # Update image in UI thread
                GLib.idle_add(self.image.set_from_pixbuf, pb)
                time.sleep(0.033)  # ~30fps
        
        self.camera_thread = threading.Thread(target=update_camera)
        self.camera_thread.daemon = True
        self.camera_thread.start()
    
    def start_authentication(self):
        """Start the authentication process in a separate thread"""
        def auth_thread():
            # Simulate authentication progress
            for i in range(1, 11):
                if self.stop_capture.is_set():
                    return
                GLib.idle_add(self.progress_bar.set_fraction, i / 10.0)
                time.sleep(0.5)
            
            # Perform the actual authentication
            self.face_verified = authenticate_user(self.username, False)
            self.auth_completed = True
            
            # Update UI based on result
            if self.face_verified:
                GLib.idle_add(self.authentication_successful)
            else:
                GLib.idle_add(self.authentication_failed)
        
        self.authentication_thread = threading.Thread(target=auth_thread)
        self.authentication_thread.daemon = True
        self.authentication_thread.start()
    
    def authentication_successful(self):
        """Called when authentication is successful"""
        self.status_label.set_text("Authentication successful!")
        self.progress_bar.set_fraction(1.0)
        
        # Exit with success after a short delay
        GLib.timeout_add(1000, self.exit_success)
    
    def authentication_failed(self):
        """Called when authentication fails"""
        self.status_label.set_text("Face not recognized")
        self.retry_button.show()
    
    def on_retry_clicked(self, button):
        """Retry face authentication"""
        self.retry_button.hide()
        self.status_label.set_text("Looking for your face...")
        self.progress_bar.set_fraction(0.0)
        self.auth_completed = False
        
        # Restart authentication
        self.start_authentication()
    
    def on_password_clicked(self, button):
        """Fall back to password authentication"""
        self.exit_failure()
    
    def exit_success(self):
        """Exit with success code"""
        self.cleanup()
        sys.exit(0)
    
    def exit_failure(self):
        """Exit with failure code"""
        self.cleanup()
        sys.exit(1)
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_capture.set()
        if self.cap:
            self.cap.release()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: face_auth_ui.py <username>")
        sys.exit(1)
        
    username = sys.argv[1]
    win = FaceAuthWindow(username)
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
