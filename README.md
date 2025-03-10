# Face Authentication System for Linux

This project implements a face recognition-based authentication system for Linux using Python and the Pluggable Authentication Modules (PAM) framework. It allows users to log into their Linux system using facial recognition as an authentication method.

## Table of Contents

- [Face Authentication System for Linux](#face-authentication-system-for-linux)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
    - [1. System Preparation](#1-system-preparation)
    - [2. Project Directory Setup](#2-project-directory-setup)
  - [Project Structure](#project-structure)
  - [Setup Process](#setup-process)
    - [3. Face Data Collection](#3-face-data-collection)
    - [4. Model Training](#4-model-training)
    - [5. PAM Module Creation](#5-pam-module-creation)
    - [6. System Integration](#6-system-integration)
  - [Usage](#usage)
  - [Troubleshooting](#troubleshooting)

## Prerequisites

- Ubuntu/Debian-based Linux distribution
- Python 3.6 or higher
- Administrator (sudo) privileges
- Webcam connected to your system

## Installation

### 1. System Preparation

Install the required system packages:

```bash
# Update package list
sudo apt update

# Install system dependencies
sudo apt install -y python3-pip python3-dev cmake build-essential pkg-config
sudo apt install -y libopencv-dev
sudo apt install -y libdlib-dev python3-venv
```

### 2. Project Directory Setup

Create and configure the project environment:

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

## Project Structure

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

## Setup Process

### 3. Face Data Collection

Create a script to collect facial data:

```bash
# Create face collection script
nano scripts/collect_faces.py
```

The code for this file can be found in `collect_faces.py` in this repository.

### 4. Model Training

Create a script to train the face recognition model:

```bash
# Create model training script
nano scripts/train_model.py
```

The code for this file can be found in `train_model.py` in this repository.

### 5. PAM Module Creation

Create PAM module files:

```bash
# Create PAM interface
nano pam_module/pam_face_auth.c
```

The code for this file can be found in `pam_face_auth.c` in this repository.

Create the face authentication script:

```bash
# Create authentication script
nano scripts/face_auth.py
```

The code for this file can be found in `face_auth.py` in this repository.

Create the Makefile for compiling the PAM module:

```bash
# Create Makefile
nano pam_module/Makefile
```

The code for this file can be found in `Makefile` in this repository.

Create a startup script to activate the virtual environment when needed:

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

### 6. System Integration

Compile and install the PAM module:

```bash
# Compile the PAM module
cd ~/face_auth_system/pam_module
make
sudo make install

# Make the face authentication script accessible system-wide
sudo cp ~/face_auth_system/scripts/face_auth.py /usr/local/bin/
sudo chmod +x /usr/local/bin/face_auth.py
```

Integrate with the Linux PAM system:

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

## Usage

1. First, collect your face data:

```bash
# Activate the virtual environment
cd ~/face_auth_system
source venv/bin/activate

# Collect face data (replace username with your Linux username)
python scripts/collect_faces.py --username nguynqh
```

2. Train the face recognition model:

```bash
python scripts/train_model.py
```

3. Test the authentication:

```bash
# The system should now be configured to authenticate using facial recognition
# You can test it by locking and unlocking your screen or by using sudo commands
```

## Troubleshooting

- **PAM Module Issues**: If there are problems with the PAM module, you can restore your original PAM configuration using:
  ```bash
  sudo cp /etc/pam.d/common-auth.backup /etc/pam.d/common-auth
  ```

- **Path Issues**: If the system can't find the face authentication script, verify that:
  1. The script is correctly installed at `/usr/local/bin/face_auth.py`
  2. The script has executable permissions
  3. The path in `pam_face_auth.c` matches your actual script path

- **Camera Issues**: Make sure your webcam is properly connected and working before using the face authentication system

---

**Note**: Remember to update the path in `pam_face_auth.c` to point to your specific username:
```c
#define FACE_AUTH_SCRIPT "/home/<username_ubuntu>/face_auth_system/start_face_auth.sh"
```

Replace with your actual username before compiling the PAM module.

**Last Updated**: 2025-03-10 (UTC)