#!/bin/bash
cd ~/face_auth_system
source venv/bin/activate
python scripts/face_auth.py "$@"
