#!/usr/bin/env python3
import cv2
import dlib
import numpy as np
import face_recognition
import os
import sys
import time
import argparse
from face_storage import FaceStorage

def register_face(username, display_ui=True):
    """Register a face for the given username"""
    storage = FaceStorage()
    
    print(f"Registering face for user: {username}")
    
    # Setup face detection
    detector = dlib.get_frontal_face_detector()
    predictor_path = "/usr/lib/face-auth/shape_predictor_68_face_landmarks.dat"
    predictor = dlib.shape_predictor(predictor_path)
    
    # Open camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot access camera")
        return False
    
    if display_ui:
        cv2.namedWindow("Face Registration")
    
    # Variables for liveness detection
    blink_count = 0
    eye_closed_frames = 0
    prev_face_location = None
    prev_light_intensity = None
    no_movement_frames = 0
    no_light_change_frames = 0
    
    def calculate_ear(eye):
        A = np.linalg.norm(eye[1] - eye[5])
        B = np.linalg.norm(eye[2] - eye[4])
        C = np.linalg.norm(eye[0] - eye[3])
        return (A + B) / (2.0 * C)
    
    # Main registration loop
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.resize(frame, (640, 480))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        if not face_locations:
            if display_ui:
                cv2.putText(frame, "No face detected", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("Face Registration", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
            continue
        
        top, right, bottom, left = face_locations[0]
        offset = 25
        top = max(0, top - offset)
        bottom = min(frame.shape[0], bottom + offset)
        left = max(0, left - offset)
        right = min(frame.shape[1], right + offset)
        
        face_crop = frame[top:bottom, left:right]
        if display_ui and face_crop.shape[0] > 0 and face_crop.shape[1] > 0:
            cv2.rectangle(frame, (left, top), (right, bottom), (34, 139, 34), 2)
        
        # Check image sharpness
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        if display_ui:
            cv2.putText(frame, f"Sharpness: {int(sharpness)}", (20, 160),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        if sharpness < 50:
            print("Warning: Detected a printed photo! Please use a real face.")
            cap.release()
            cv2.destroyAllWindows()
            return False
        
        # Check lighting changes
        light_intensity = np.mean(gray[top:bottom, left:right])
        if prev_light_intensity is not None:
            if abs(light_intensity - prev_light_intensity) < 15:
                no_light_change_frames += 1
            else:
                no_light_change_frames = 0
            if no_light_change_frames >= 45:
                print("Warning: No lighting change detected!")
                cap.release()
                cv2.destroyAllWindows()
                return False
        prev_light_intensity = light_intensity
        
        # Check movement
        if prev_face_location is not None:
            dx = abs(prev_face_location[3] - left) + abs(prev_face_location[1] - right)
            dy = abs(prev_face_location[0] - top) + abs(prev_face_location[2] - bottom)
            if dx < 25 and dy < 25:
                no_movement_frames += 1
            else:
                no_movement_frames = 0
            if no_movement_frames >= 30:
                print("Warning: No movement detected!")
                cap.release()
                cv2.destroyAllWindows()
                return False
        prev_face_location = face_locations[0]
        
        # Detect blinks
        rects = detector(gray, 0)
        for rect in rects:
            shape = predictor(gray, rect)
            shape_np = np.zeros((68, 2), dtype=int)
            for i in range(68):
                shape_np[i] = (shape.part(i).x, shape.part(i).y)
                
            leftEye = shape_np[36:42]
            rightEye = shape_np[42:48]
            ear = (calculate_ear(leftEye) + calculate_ear(rightEye)) / 2.0
            if ear < 0.22:
                eye_closed_frames += 1
            else:
                if eye_closed_frames >= 2:
                    blink_count += 1
                    eye_closed_frames = 0
            
            if display_ui:
                cv2.putText(frame, f"Blinks: {blink_count}", (50, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if blink_count >= 4 and display_ui:
            cv2.putText(frame, "Valid face! Press 's' to save", (50, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if display_ui:
            cv2.imshow("Face Registration", frame)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord("s"):
                if blink_count < 4:
                    print("Warning: Please blink to verify!")
                else:
                    # Save face encoding
                    face_encodings = face_recognition.face_encodings(rgb_frame, [face_locations[0]])
                    if face_encodings:
                        # Save encoding to file
                        encoding = np.array(face_encodings[0], dtype=np.float64)
                        if storage.save_face_encoding(username, encoding.tobytes()):
                            print(f"Face saved for {username}!")
                            cap.release()
                            cv2.destroyAllWindows()
                            return True
                        else:
                            print("Error: Failed to save face data")
            elif key == ord("q"):
                break
        elif blink_count >= 4:
            # In non-UI mode, save automatically when conditions are met
            face_encodings = face_recognition.face_encodings(rgb_frame, [face_locations[0]])
            if face_encodings:
                encoding = np.array(face_encodings[0], dtype=np.float64)
                if storage.save_face_encoding(username, encoding.tobytes()):
                    print(f"Face saved for {username}!")
                    cap.release()
                    cv2.destroyAllWindows()
                    return True
    
    cap.release()
    cv2.destroyAllWindows()
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register facial recognition for a user")
    parser.add_argument("username", help="Username to register face for")
    parser.add_argument("--no-ui", action="store_true", help="Run without UI (for scripts)")
    args = parser.parse_args()
    
    if os.geteuid() != 0:
        print("Error: This program must be run as root")
        sys.exit(1)
        
    if register_face(args.username, not args.no_ui):
        sys.exit(0)
    else:
        sys.exit(1)
