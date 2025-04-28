🔐 Face Authentication System for Ubuntu 24.04

Python 3.10+ Ubuntu OpenCV GTK3

Secure your Ubuntu system with facial recognition - seamlessly integrated with system login, sudo, and lock screen
📋 Table of Contents

    🔐 Face Authentication System for Ubuntu 24.04
        📋 Table of Contents
        ✨ Features
        🔧 Prerequisites
        📥 Installation
            Automatic Installation
            Manual Installation
        📁 Project Structure
        🛠️ Configuration
            1. PAM Configuration
            2. Face Registration
            3. Testing the Authentication
        📝 Usage
        ❓ Common Issues & Troubleshooting
            NumPy Version Issues
            Permission Denied Errors
            Lock Screen Not Working
        🔒 Security Notes
        📊 Performance Factors

✨ Features

    👤 Seamless Integration: Works with system login, sudo, and lock screen
    🔌 PAM Integration: Integrates with Linux's Pluggable Authentication Modules
    🛡️ Privacy-Focused: All processing is done locally, no data sent to external servers
    🌙 Liveness Detection: Blink detection to prevent photo-based spoofing
    🚪 Multi-context Support: GDM, LightDM, and console login support
    🖥️ Modern GTK Interface: Clean, responsive interface for face registration

🔧 Prerequisites

    Ubuntu 24.04 LTS
    Python 3.10 or higher
    Administrator (sudo) privileges
    Working webcam
    Proper lighting conditions

📥 Installation
Automatic Installation

The easiest way to install the system is using the provided installation script:
bash

# Clone the repository (or download and extract)
git clone https://github.com/nguynqh/face-auth.git
cd face-auth

# Make the installation script executable
chmod +x install.sh

# Run the installation script
sudo ./install.sh

After installation, register your face:
bash

sudo face_auth_register

Manual Installation

If you prefer to install manually, follow these steps:

    Install Dependencies

bash

# Update package list
sudo apt update

# Install system dependencies
sudo apt install -y build-essential libpam0g-dev libgtk-3-dev python3-pip \
    python3-dev python3-opencv python3-gi python3-cairo python3-gi-cairo \
    gir1.2-gtk-3.0 v4l-utils cmake

# Install Python libraries (using a specific NumPy version to avoid conflicts)
sudo pip3 install face-recognition dlib numpy==1.26.4 imutils

    Install Python Modules and PAM Module

bash

# Create necessary directories
sudo mkdir -p /usr/lib/face-auth/face_auth
sudo mkdir -p /usr/share/face-auth
sudo mkdir -p /var/lib/face-auth

# Compile and install PAM module
cd pam_module
make
sudo make install

# Install Python files
sudo cp face_auth/*.py /usr/lib/face-auth/face_auth/
sudo cp face_auth_ui/*.py /usr/lib/face-auth/

# Create symbolic links
sudo ln -sf /usr/lib/face-auth/face_auth_ui/auth_ui.py /usr/bin/face_auth_ui
sudo ln -sf /usr/lib/face-auth/face_auth_ui/register_ui.py /usr/bin/face_auth_register_ui
sudo chmod +x /usr/bin/face_auth_ui
sudo chmod +x /usr/bin/face_auth_register_ui

# Install registration script
sudo cp utils/face_auth_register /usr/bin/
sudo chmod +x /usr/bin/face_auth_register

# Create Python module structure
sudo touch /usr/lib/face-auth/face_auth/__init__.py

# Install service
sudo cp systemd/face-auth.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable face-auth.service
sudo systemctl start face-auth.service

    Configure PAM

bash

# Back up original PAM configuration
sudo cp /etc/pam.d/gdm-password /etc/pam.d/gdm-password.bak

# Add face authentication to PAM (after pam_succeed_if.so and before @include common-auth)
sudo nano /etc/pam.d/gdm-password

Add this line after auth required pam_succeed_if.so user != root quiet_success:
Code

auth    sufficient      pam_face_auth.so

📁 Project Structure
Code

/usr/lib/face-auth/
├── face_auth/             # Core authentication library
│   ├── __init__.py
│   ├── authenticator.py   # Authentication logic
│   └── service.py         # Background service
├── face_auth_ui/
│   ├── auth_ui.py         # Authentication UI
│   └── register_ui.py     # Registration UI

/usr/bin/
├── face_auth_ui           # Symlink to auth_ui.py
├── face_auth_register_ui  # Symlink to register_ui.py
└── face_auth_register     # User-friendly registration script

/var/lib/face-auth/        # Stores user face data
├── nguynqh.txt            # Your face encoding data
└── ...

/usr/share/face-auth/      # Shared resources
└── shape_predictor_68_face_landmarks.dat  # Dlib model file

/lib/security/
└── pam_face_auth.so       # PAM module

🛠️ Configuration
1. PAM Configuration

PAM must be configured for each authentication context where you want to use face authentication:

    For Login Screen (GDM)

bash

sudo nano /etc/pam.d/gdm-password

Add after auth required pam_succeed_if.so user != root quiet_success:
Code

auth    sufficient      pam_face_auth.so

    For Lock Screen

bash

sudo cp /etc/pam.d/gdm-password /etc/pam.d/gnome-screensaver

    For sudo (Optional)

bash

sudo cp /etc/pam.d/sudo /etc/pam.d/sudo.bak
sudo nano /etc/pam.d/sudo

Add after @include common-auth:
Code

auth    sufficient      pam_face_auth.so

2. Face Registration

Register your face using the registration utility:
bash

sudo face_auth_register

Or for a specific user:
bash

sudo face_auth_register username

This will open a GTK interface where you'll be guided through the registration process:

    Click "Start" to begin registration
    Look directly at the camera and blink 3 times when prompted
    The system will automatically capture your face encoding when completed

3. Testing the Authentication

Test if the authentication works:
bash

face_auth_test

This will simulate the authentication process without actually authenticating, allowing you to verify that your face is recognized correctly.
📝 Usage

Once installed and configured, the face authentication system works seamlessly:

    Login Screen: When you reach the login screen, the system will attempt to authenticate you using facial recognition. If successful, you'll be logged in without entering a password.

    Lock Screen: When unlocking your screen, facial recognition will attempt to authenticate you automatically.

    sudo Commands: If configured, when you run a command with sudo, you can authenticate using your face instead of typing your password.

If facial authentication fails, the system will fall back to password authentication.
❓ Common Issues & Troubleshooting
NumPy Version Issues

Symptom: Error message about NumPy 1.x vs NumPy 2.x compatibility.

Solution: Downgrade NumPy to a compatible version:
bash

sudo pip3 install numpy==1.26.4 --force-reinstall

Permission Denied Errors

Symptom: Permission denied errors when accessing files:
Code

Permission denied: '/var/lib/face-auth/nguynqh.txt'

or
Code

Permission denied: '/var/log/face-auth.log'

Solution: Fix permissions with:
bash

# For face data directory
sudo chmod 775 /var/lib/face-auth
sudo touch /var/lib/face-auth/nguynqh.txt
sudo chown nguynqh:nguynqh /var/lib/face-auth/nguynqh.txt
sudo chmod 644 /var/lib/face-auth/nguynqh.txt

# For log files
sudo mkdir -p /var/log/face-auth
sudo touch /var/log/face-auth.log
sudo chmod 666 /var/log/face-auth.log

Lock Screen Not Working

Symptom: Face authentication works for login and sudo but not for the lock screen.

Solution: Create or update the gnome-screensaver PAM configuration:
bash

sudo cp /etc/pam.d/gdm-password /etc/pam.d/gnome-screensaver

If that doesn't work, check Wayland-specific configurations:
bash

# Create a policy for camera access on lock screen
sudo nano /etc/polkit-1/localauthority/50-local.d/45-allow-camera-lock-screen.pkla

Add:
Code

[Allow Camera Access on Lock Screen]
Identity=unix-user:*
Action=org.freedesktop.login1.session-self-access-devices;org.freedesktop.camera.access
ResultAny=yes
ResultInactive=yes
ResultActive=yes

🔒 Security Notes

    Face authentication adds convenience but may not be as secure as a strong password for highly sensitive systems
    Use good lighting for better recognition accuracy
    For maximum security, consider using face authentication alongside traditional password authentication
    The system uses liveness detection (blinking) to help prevent photo-based spoofing

📊 Performance Factors

The system's performance depends on several factors:

    Lighting: Good, consistent lighting improves recognition accuracy
    Camera quality: Higher resolution cameras provide better facial details
    System resources: Face recognition requires moderate CPU power
    Distance from camera: Optimal distance is typically 30-60cm from the camera
    Face position: Straight-on face view works best

