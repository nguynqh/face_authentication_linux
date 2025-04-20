#!/usr/bin/env python3
import cv2
import dlib
import numpy as np
import face_recognition
import os
import sys
import time
from face_storage import FaceStorage

def shape_to_np(shape, dtype="int"):
    coords = np.zeros((68, 2), dtype=dtype)
    for i in range(68):
        coords[i] = (shape.part(i).x, shape.part(i).y)
    return coords

def calculate_ear(eye):
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    return (A + B) / (2.0 * C)

def authenticate_user(username, display_ui=False):
    """
    Authenticate a user using facial recognition
    Returns: True if authenticated, False otherwise
    """
    storage = FaceStorage()
    
    # Get stored face encoding
    stored_encoding = storage.get_face_encoding(username)
    if stored_encoding is None or stored_encoding.shape != (128,):
        print("No valid face ID registered for this user.")
        return False
        
    # Setup face detection
    detector = dlib.get_frontal_face_detector()
    predictor_path = "/usr/lib/face-auth/shape_predictor_68_face_landmarks.dat"
    predictor = dlib.shape_predictor(predictor_path)
    
    # Prepare the camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Unable to access camera")
        return False
    
    # Authentication parameters
    EAR_THRESHOLD = 0.25
    REQUIRED_BLINKS = 2
    SHARPNESS_THRESHOLD = 100  # Relaxed for real-world use
    FACE_MATCH_THRESHOLD = 0.45
    MAX_ATTEMPTS = 50  # About 5 seconds
    
    blink_count = 0
    eye_closed_frames = 0
    eye_blinking = False
    face_verified = False
    attempt_count = 0
    
    # For optional UI display
    if display_ui:
        cv2.namedWindow("Face Authentication", cv2.WINDOW_NORMAL)
    
    # Main authentication loop
    while attempt_count < MAX_ATTEMPTS:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.resize(frame, (640, 480))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb)
        
        if not face_locations:
            attempt_count += 1
            if display_ui:
                cv2.putText(frame, "No face detected", (20, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("Face Authentication", frame)
                cv2.waitKey(1)
            continue
        
        # Check sharpness to prevent photo attacks
        top, right, bottom, left = face_locations[0]
        face_crop = gray[top:bottom, left:right]
        sharpness = cv2.Laplacian(face_crop, cv2.CV_64F).var()
        
        if sharpness < SHARPNESS_THRESHOLD:
            print("Image too blurry - possible spoofing attempt")
            cap.release()
            cv2.destroyAllWindows()
            return False
            
        # Detect blinks
        rects = detector(gray, 0)
        if rects:
            shape = predictor(gray, rects[0])
            shape = shape_to_np(shape)
            leftEye = shape[42:48]
            rightEye = shape[36:42]
            ear = (calculate_ear(leftEye) + calculate_ear(rightEye)) / 2.0
            
            if ear < EAR_THRESHOLD:
                eye_closed_frames += 1
                eye_blinking = True
            else:
                if eye_blinking and eye_closed_frames >= 2:
                    blink_count += 1
                eye_closed_frames = 0
                eye_blinking = False
                
        # Check face match
        if attempt_count % 5 == 0:
            face_encodings = face_recognition.face_encodings(rgb, face_locations)
            if face_encodings:
                current_encoding = face_encodings[0]
                distance = np.linalg.norm(current_encoding - stored_encoding)
                
                if distance < FACE_MATCH_THRESHOLD:
                    face_verified = True
                    
        # Display status if UI is enabled
        if display_ui:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, f"Blink: {blink_count}", (20, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.imshow("Face Authentication", frame)
            cv2.waitKey(1)
                    
        # Check if authentication completed
        if blink_count >= REQUIRED_BLINKS and face_verified:
            cap.release()
            cv2.destroyAllWindows()
            return True
            
        attempt_count += 1
    
    # If we got here, authentication failed
    cap.release()
    cv2.destroyAllWindows()
    return False
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: face_auth_cli.py <username> [--ui]")
        sys.exit(1)
        
    username = sys.argv[1]
    display_ui = "--ui" in sys.argv
    
    if authenticate_user(username, display_ui):
        print("Authentication successful")
        sys.exit(0)
    else:
        print("Authentication failed")
        sys.exit(1)
