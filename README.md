# 🔐 Face Authentication System for Ubuntu 24.04

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?style=flat&logo=ubuntu&logoColor=white)](https://ubuntu.com/)
[![OpenCV](https://img.shields.io/badge/opencv-%23white.svg?style=flat&logo=opencv&logoColor=white)](https://opencv.org/)
[![GTK3](https://img.shields.io/badge/GTK-3.0-blue.svg?style=flat&logo=gtk&logoColor=white)](https://www.gtk.org/)

*Secure your Ubuntu system with facial recognition - seamlessly integrated with system login, sudo, and lock screen*

## 📋 Table of Contents

- [🔐 Face Authentication System for Ubuntu 24.04](#-face-authentication-system-for-ubuntu-2404)
  - [📋 Table of Contents](#-table-of-contents)
  - [✨ Features](#-features)
  - [🔧 Prerequisites](#-prerequisites)
  - [📥 Installation](#-installation)
    - [Automatic Installation](#automatic-installation)
    - [Manual Installation](#manual-installation)
  - [📁 Project Structure](#-project-structure)
  - [🛠️ Configuration](#️-configuration)
    - [1. PAM Configuration](#1-pam-configuration)
    - [2. Face Registration](#2-face-registration)
    - [3. Testing the Authentication](#3-testing-the-authentication)
  - [📝 Usage](#-usage)
  - [❓ Common Issues & Troubleshooting](#-common-issues--troubleshooting)
    - [NumPy Version Issues](#numpy-version-issues)
    - [Permission Denied Errors](#permission-denied-errors)
    - [Lock Screen Not Working](#lock-screen-not-working)
  - [🔒 Security Notes](#-security-notes)
  - [📊 Performance Factors](#-performance-factors)

## ✨ Features

- 👤 **Seamless Integration**: Works with system login, sudo, and lock screen
- 🔌 **PAM Integration**: Integrates with Linux's Pluggable Authentication Modules
- 🛡️ **Privacy-Focused**: All processing is done locally, no data sent to external servers
- 🌙 **Liveness Detection**: Blink detection to prevent photo-based spoofing
- 🚪 **Multi-context Support**: GDM, LightDM, and console login support
- 🖥️ **Modern GTK Interface**: Clean, responsive interface for face registration

## 🔧 Prerequisites

- Ubuntu 24.04 LTS
- Python 3.10 or higher
- Administrator (sudo) privileges
- Working webcam
- Proper lighting conditions

## 📥 Installation

### Automatic Installation

The easiest way to install the system is using the provided installation script:

```bash
# Clone the repository (or download and extract)
git clone https://github.com/nguynqh/face-auth.git
cd face-auth

# Make the installation script executable
chmod +x install.sh

# Run the installation script
sudo ./install.sh
