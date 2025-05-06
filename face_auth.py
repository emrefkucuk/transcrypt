import os
import uuid
import base64
import logging
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import cv2
from deepface import DeepFace

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure face database directory
FACE_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_db")
os.makedirs(FACE_DB_DIR, exist_ok=True)

class FaceAuth:
    def __init__(self):
        """Initialize the face authentication system"""
        # Map of room_id -> list of user face directories
        self.room_faces: Dict[str, List[str]] = {}
        # Configure face detection and recognition settings
        self.model_name = "VGG-Face"  # Default recognition model
        self.detector_backend = "opencv"  # Default detector
        self.distance_metric = "cosine"  # Default distance metric
        self.similarity_threshold = 0.35  # Threshold for face matching (lower means more strict)
        
        # Ensure face database directory exists
        os.makedirs(FACE_DB_DIR, exist_ok=True)
        # Load existing rooms if any
        self._load_existing_rooms()
        
        logger.info(f"Face authentication initialized with model: {self.model_name}")

    def _load_existing_rooms(self):
        """Load existing room directories from face_db"""
        if not os.path.exists(FACE_DB_DIR):
            return
            
        for room_dir in os.listdir(FACE_DB_DIR):
            room_path = os.path.join(FACE_DB_DIR, room_dir)
            if os.path.isdir(room_path) and room_dir.startswith("room_"):
                room_id = room_dir[5:]  # Remove "room_" prefix
                self.room_faces[room_id] = []
                
                # Load user directories for this room
                for user_dir in os.listdir(room_path):
                    user_path = os.path.join(room_path, user_dir)
                    if os.path.isdir(user_path) and user_dir.startswith("user_"):
                        self.room_faces[room_id].append(user_path)
                        
        logger.info(f"Loaded {len(self.room_faces)} existing face-auth rooms")

    def create_room_with_faces(self, room_id: str, face_images: List[bytes]) -> Tuple[bool, str]:
        """
        Create a new room with authorized face images
        
        Args:
            room_id: Unique identifier for the room
            face_images: List of face images as bytes
            
        Returns:
            Tuple of (success, message)
        """
        if not face_images:
            return False, "No face images provided"
            
        # Create room directory
        room_dir = os.path.join(FACE_DB_DIR, f"room_{room_id}")
        os.makedirs(room_dir, exist_ok=True)
        
        # Initialize room in mapping
        self.room_faces[room_id] = []
        
        # Process each face image
        valid_faces = 0
        
        # Group images by user
        user_id = str(uuid.uuid4())[:8]
        user_dir = os.path.join(room_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        
        for i, face_image_bytes in enumerate(face_images):
            try:
                # Convert bytes to numpy array
                nparr = np.frombuffer(face_image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Detect if there's a face in the image
                face_objs = DeepFace.extract_faces(
                    img_path=img,
                    detector_backend=self.detector_backend,
                    enforce_detection=True
                )
                
                if not face_objs or len(face_objs) == 0:
                    logger.warning(f"No face detected in image {i} for room {room_id}")
                    continue
                
                # Save the face image
                face_filename = os.path.join(user_dir, f"face_{i}.jpg")
                cv2.imwrite(face_filename, img)
                
                valid_faces += 1
                
            except Exception as e:
                logger.error(f"Error processing face image {i}: {str(e)}")
                continue
        
        # If no valid faces, clean up and return error
        if valid_faces == 0:
            import shutil
            shutil.rmtree(room_dir)
            return False, "No valid faces detected in the provided images"
            
        # Add the user directory to room mapping
        self.room_faces[room_id].append(user_dir)
        
        return True, f"Room created with {valid_faces} valid face images"
    
    def add_user_to_room(self, room_id: str, face_images: List[bytes]) -> Tuple[bool, str]:
        """
        Add a new authorized user to an existing room
        
        Args:
            room_id: Room identifier
            face_images: List of face images for the new user
            
        Returns:
            Tuple of (success, message)
        """
        if room_id not in self.room_faces:
            return False, "Room not found"
            
        if not face_images:
            return False, "No face images provided"
        
        # Get room directory
        room_dir = os.path.join(FACE_DB_DIR, f"room_{room_id}")
        if not os.path.exists(room_dir):
            os.makedirs(room_dir, exist_ok=True)
        
        # Create new user directory
        user_id = str(uuid.uuid4())[:8]
        user_dir = os.path.join(room_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        
        # Process each face image
        valid_faces = 0
        
        for i, face_image_bytes in enumerate(face_images):
            try:
                # Convert bytes to numpy array
                nparr = np.frombuffer(face_image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Detect if there's a face in the image
                face_objs = DeepFace.extract_faces(
                    img_path=img,
                    detector_backend=self.detector_backend,
                    enforce_detection=True
                )
                
                if not face_objs or len(face_objs) == 0:
                    logger.warning(f"No face detected in image {i} for user {user_id}")
                    continue
                
                # Save the face image
                face_filename = os.path.join(user_dir, f"face_{i}.jpg")
                cv2.imwrite(face_filename, img)
                
                valid_faces += 1
                
            except Exception as e:
                logger.error(f"Error processing face image {i}: {str(e)}")
                continue
        
        # If no valid faces, clean up and return error
        if valid_faces == 0:
            import shutil
            shutil.rmtree(user_dir)
            return False, "No valid faces detected in the provided images"
            
        # Add the user directory to room mapping
        self.room_faces[room_id].append(user_dir)
        
        return True, f"Added new user with {valid_faces} valid face images"
    
    def verify_face_for_rooms(self, face_image_bytes: bytes) -> List[str]:
        """
        Verify if a face matches any authorized user in any room
        
        Args:
            face_image_bytes: Image of the face to verify
            
        Returns:
            List of room IDs where the face is authorized
        """
        if not face_image_bytes:
            return []
            
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(face_image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Detect if there's a face in the image
            try:
                face_objs = DeepFace.extract_faces(
                    img_path=img,
                    detector_backend=self.detector_backend,
                    enforce_detection=True
                )
                
                if not face_objs or len(face_objs) == 0:
                    logger.warning(f"No face detected in verification image")
                    return []
            except Exception as e:
                logger.error(f"Error detecting face: {str(e)}")
                return []
            
            # Verify against all rooms
            authorized_rooms = []
            
            for room_id, user_dirs in self.room_faces.items():
                for user_dir in user_dirs:
                    # Check if the directory exists
                    if not os.path.exists(user_dir):
                        continue
                        
                    # Get all face images for this user
                    face_files = [
                        os.path.join(user_dir, f) for f in os.listdir(user_dir)
                        if f.endswith(('.jpg', '.jpeg', '.png'))
                    ]
                    
                    if not face_files:
                        continue
                    
                    # Check if the face matches any of the user's faces
                    for face_file in face_files:
                        try:
                            # Verify face match
                            result = DeepFace.verify(
                                img1_path=img,
                                img2_path=face_file,
                                model_name=self.model_name,
                                detector_backend=self.detector_backend,
                                distance_metric=self.distance_metric,
                                enforce_detection=False  # Already verified once
                            )
                            
                            # If matched, add the room to authorized rooms
                            if result.get("verified", False):
                                logger.info(f"Face verified for room {room_id}")
                                authorized_rooms.append(room_id)
                                # Break out of face files loop once matched
                                break
                                
                        except Exception as e:
                            logger.error(f"Error verifying against face {face_file}: {str(e)}")
                            continue
                    
                    # If already authorized for this room, move to next room
                    if room_id in authorized_rooms:
                        break
            
            return authorized_rooms
                
        except Exception as e:
            logger.error(f"Error in face verification: {str(e)}")
            return []
    
    def delete_room(self, room_id: str) -> bool:
        """
        Delete a room and all associated face data
        
        Args:
            room_id: Room identifier to delete
            
        Returns:
            True if successful, False otherwise
        """
        if room_id not in self.room_faces:
            return False
            
        try:
            # Remove from memory
            self.room_faces.pop(room_id, None)
            
            # Remove from disk
            room_dir = os.path.join(FACE_DB_DIR, f"room_{room_id}")
            if os.path.exists(room_dir):
                import shutil
                shutil.rmtree(room_dir)
                
            return True
        except Exception as e:
            logger.error(f"Error deleting room {room_id}: {str(e)}")
            return False

# Create a singleton instance
face_auth = FaceAuth()