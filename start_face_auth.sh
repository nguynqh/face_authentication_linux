#!/bin/bash
# Navigate to the project directory
cd /home/izzy/Documents/face_authentication_linux || exit 1 
# Activate the virtual environment
source venv/bin/activate || exit 1
# Run the face authentication script
python scripts/face_auth.py "$@"
