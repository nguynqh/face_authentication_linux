# 🔐 Face Authentication System for Linux

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=flat&logo=ubuntu&logoColor=white)](https://ubuntu.com/)
[![OpenCV](https://img.shields.io/badge/opencv-%23white.svg?style=flat&logo=opencv&logoColor=white)](https://opencv.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-%23FF6F00.svg?style=flat&logo=TensorFlow&logoColor=white)](https://www.tensorflow.org/)

<div align="center">

![Face Recognition Banner](https://i.imgur.com/placeholder-image.png)

*Secure your Linux system with the power of facial recognition technology*

</div>

## 📋 Table of Contents

- [🔐 Face Authentication System for Linux](#-face-authentication-system-for-linux)
  - [📋 Table of Contents](#-table-of-contents)
  - [✨ Features](#-features)
  - [🔧 Prerequisites](#-prerequisites)
  - [📥 Installation](#-installation)
    - [1. System Preparation](#1-system-preparation)
    - [2. Project Directory Setup](#2-project-directory-setup)
  - [📁 Project Structure](#-project-structure)
  - [🛠️ Setup Process](#️-setup-process)
    - [3. Face Data Collection](#3-face-data-collection)
    - [4. Model Training](#4-model-training)
    - [5. PAM Module Creation](#5-pam-module-creation)
    - [6. System Integration](#6-system-integration)
  - [📝 Usage](#-usage)
  - [❓ Troubleshooting](#-troubleshooting)
  - [🔒 Security Notes](#-security-notes)
  - [📊 Performance](#-performance)
  - [📜 License](#-license)

## ✨ Features

- 👤 **Facial Recognition Authentication**: Log in using your face instead of typing passwords
- 🔌 **PAM Integration**: Works with Linux's Pluggable Authentication Modules
- 🛡️ **Security**: Local processing of facial data for enhanced privacy 
- 🚪 **System-Wide Access**: Use with login screen, sudo commands, and screen unlock

## 🔧 Prerequisites

- **Ubuntu/Debian-based** Linux distribution
- **Python 3.6** or higher
- **Administrator** (sudo) privileges
- **Webcam** connected to your system

## 📥 Installation

### 1. System Preparation

<details>
<summary>📦 Install required system packages (click to expand)</summary>

```bash
# Update package list
sudo apt update

# Install system dependencies
sudo apt install -y python3-pip python3-dev cmake build-essential pkg-config
sudo apt install -y libopencv-dev
sudo apt install -y libdlib-dev python3-venv
```
</details>

### 2. Project Directory Setup

<details>
<summary>🗂️ Create and configure the project environment (click to expand)</summary>

```bash
# Create project directory
mkdir -p ~/face_auth_system
cd ~/face_auth_system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required Python packages
pip install numpy scikit-learn scikit-image pillow
pip install tensorflow
pip install face_recognition dlib opencv-python

# Create project structure
mkdir -p models data scripts utils pam_module
```
</details>

## 📁 Project Structure

After setup, your project directory should look like this:

```
face_auth_system/
├── venv/                   # Python virtual environment
├── data/                   # For storing face data
├── models/                 # For trained models
├── scripts/                # Python scripts
│   ├── collect_faces.py
│   ├── train_model.py
│   └── face_auth.py
├── utils/                  # Utility functions
└── pam_module/             # PAM integration files
    ├── pam_face_auth.c
    └── Makefile
```

## 🛠️ Setup Process

### 3. Face Data Collection

<details>
<summary>📸 Create a script to collect facial data (click to expand)</summary>

```bash
# Create face collection script
nano scripts/collect_faces.py
```

The code for this file can be found in `collect_faces.py` in this repository.
</details>

### 4. Model Training

<details>
<summary>🧠 Create a script to train the face recognition model (click to expand)</summary>

```bash
# Create model training script
nano scripts/train_model.py
```

The code for this file can be found in `train_model.py` in this repository.
</details>

### 5. PAM Module Creation

<details>
<summary>🔗 Create PAM module files (click to expand)</summary>

```bash
# Create PAM interface
nano pam_module/pam_face_auth.c
```

The code for this file can be found in `pam_face_auth.c` in this repository.

```bash
# Create authentication script
nano scripts/face_auth.py
```

The code for this file can be found in `face_auth.py` in this repository.

```bash
# Create Makefile
nano pam_module/Makefile
```

The code for this file can be found in `Makefile` in this repository.

```bash
# Create startup script
nano start_face_auth.sh
```

Add the following code to `start_face_auth.sh`:

```bash
#!/bin/bash
# Path to the virtual environment
VENV_PATH=~/face_auth_system/venv
# Activate the virtual environment and run the face auth script
source $VENV_PATH/bin/activate
python /usr/local/bin/face_auth.py "$@"
```

Make the script executable:

```bash
chmod +x ~/face_auth_system/start_face_auth.sh
```
</details>

### 6. System Integration

<details>
<summary>🔧 Compile and install the PAM module (click to expand)</summary>

```bash
# Compile the PAM module
cd ~/face_auth_system/pam_module
make
sudo make install

# Make the face authentication script accessible system-wide
sudo cp ~/face_auth_system/scripts/face_auth.py /usr/local/bin/
sudo chmod +x /usr/local/bin/face_auth.py
```
</details>

<details>
<summary>⚙️ Integrate with the Linux PAM system (click to expand)</summary>

```bash
# Backup the original PAM configuration (IMPORTANT!)
sudo cp /etc/pam.d/common-auth /etc/pam.d/common-auth.backup

# Edit the PAM configuration file
sudo nano /etc/pam.d/common-auth
```

Add the following line before `@include common-auth` or at the beginning of the file if that line doesn't exist:

```
auth sufficient pam_face_auth.so
```
</details>

## 📝 Usage

<div class="usage-container" style="background-color: #f8f8f8; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50;">

1. **First, collect your face data:**

```bash
# Activate the virtual environment
cd ~/face_auth_system
source venv/bin/activate

# Collect face data (replace username with your Linux username)
python scripts/collect_faces.py --username nguynqh
```

2. **Train the face recognition model:**

```bash
python scripts/train_model.py
```

3. **Test the authentication:**

The system should now be configured to authenticate using facial recognition.
You can test it by locking and unlocking your screen or by using sudo commands.

</div>

## ❓ Troubleshooting

<table>
  <tr>
    <th>Problem</th>
    <th>Solution</th>
  </tr>
  <tr>
    <td>⚠️ <b>PAM Module Issues</b></td>
    <td>If there are problems with the PAM module, restore your original PAM configuration using:
    <pre>sudo cp /etc/pam.d/common-auth.backup /etc/pam.d/common-auth</pre></td>
  </tr>
  <tr>
    <td>⚠️ <b>Path Issues</b></td>
    <td>If the system can't find the face authentication script, verify that:
    <ol>
      <li>The script is correctly installed at <code>/usr/local/bin/face_auth.py</code></li>
      <li>The script has executable permissions</li>
      <li>The path in <code>pam_face_auth.c</code> matches your actual script path</li>
    </ol></td>
  </tr>
  <tr>
    <td>⚠️ <b>Camera Issues</b></td>
    <td>Make sure your webcam is properly connected and working before using the face authentication system</td>
  </tr>
</table>

## 🔒 Security Notes

> ⚠️ **Important:** Face recognition should be used as a convenience feature rather than the sole authentication method for highly sensitive systems.

For enhanced security, consider:
- Using face authentication alongside traditional password authentication
- Regularly updating your facial data as your appearance changes
- Ensuring good lighting conditions for optimal recognition

## 📊 Performance

The system performance depends on:
- **Hardware**: Systems with better CPUs/GPUs will process facial recognition faster
- **Lighting**: Good lighting improves recognition accuracy
- **Camera quality**: Higher resolution cameras provide better facial detail

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<div align="center">

**Made with ❤️ by nguynqh**

**Last Updated**: 2025-03-10 (UTC)

</div>

> 💡 **Note**: Remember to update the path in `pam_face_auth.c` to point to your specific username:
> ```c
> #define FACE_AUTH_SCRIPT "/home/<username_ubuntu>/face_auth_system/start_face_auth.sh"
> ```
> Replace with your actual username before compiling the PAM module.