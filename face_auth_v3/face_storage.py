import os
import numpy as np
import json
import base64
from pathlib import Path
import pwd

class FaceStorage:
    def __init__(self):
        self.storage_dir = Path("/var/lib/face-auth/encodings")
        os.makedirs(self.storage_dir, exist_ok=True)
        os.chmod(self.storage_dir, 0o700)  # Secure permissions
    
    def get_encoding_path(self, username):
        """Get the path where the face encoding for a user is stored"""
        return self.storage_dir / f"{username}.json"
    
    def save_face_encoding(self, username, encoding):
        """Save a user's face encoding to disk"""
        # Convert numpy array to base64 string for storage
        encoding_base64 = base64.b64encode(encoding).decode('utf-8')
        
        data = {
            "username": username,
            "encoding": encoding_base64
        }
        
        # Save to file with secure permissions
        file_path = self.get_encoding_path(username)
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        os.chmod(file_path, 0o600)  # Only readable by root
        return True
    
    def get_face_encoding(self, username):
        """Retrieve a user's face encoding"""
        file_path = self.get_encoding_path(username)
        
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Convert base64 back to numpy array
            encoding_bytes = base64.b64decode(data["encoding"])
            encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
            
            return encoding
        except Exception as e:
            print(f"Error loading face encoding: {e}")
            return None
    
    def user_has_face_id(self, username):
        """Check if a user has registered face ID"""
        return self.get_encoding_path(username).exists()
