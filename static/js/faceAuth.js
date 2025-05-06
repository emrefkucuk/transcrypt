// filepath: c:\Users\Burak\Desktop\Masaustu\Projeler\_BitirmeProjeleri\encryption_api\static\js\faceAuth.js
// faceAuth.js - Handles face authentication functionality
import { showNotification, addLogEntry } from './ui.js';
import { joinRoomWithKey } from './roomJoining.js';

// Global variables for webcam handling
let videoStream = null;
let capturedPhotoBlob = null;

// Start the webcam
export function startCamera() {
    const video = document.getElementById('webcamVideo');
    const placeholder = document.getElementById('webcamPlaceholder');
    const captureBtn = document.getElementById('capturePhotoBtn');
    
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(function(stream) {
                videoStream = stream;
                video.srcObject = stream;
                video.play();
                
                // Hide placeholder, show video
                placeholder.style.display = 'none';
                video.style.display = 'block';
                
                // Enable capture button
                captureBtn.disabled = false;
                
                addLogEntry('Camera started successfully', 'info');
            })
            .catch(function(error) {
                showNotification('Could not access camera: ' + error.message, 'danger');
                addLogEntry('Camera access error: ' + error.message, 'error');
            });
    } else {
        showNotification('Your browser does not support camera access', 'danger');
        addLogEntry('Browser does not support getUserMedia', 'error');
    }
}

// Stop the webcam
export function stopCamera() {
    if (videoStream) {
        videoStream.getTracks().forEach(track => {
            track.stop();
        });
        videoStream = null;
        
        const video = document.getElementById('webcamVideo');
        const placeholder = document.getElementById('webcamPlaceholder');
        const captureBtn = document.getElementById('capturePhotoBtn');
        
        // Hide video, show placeholder
        video.style.display = 'none';
        placeholder.style.display = 'flex';
        
        // Disable capture button
        captureBtn.disabled = true;
        
        addLogEntry('Camera stopped', 'info');
    }
}

// Capture a photo from the webcam
export function capturePhoto() {
    if (!videoStream) {
        showNotification('Camera is not active', 'warning');
        return;
    }
    
    const video = document.getElementById('webcamVideo');
    const canvas = document.getElementById('webcamCanvas');
    const capturedPhoto = document.getElementById('capturedPhoto');
    const capturedContainer = document.getElementById('capturedPhotoContainer');
    const verifyBtn = document.getElementById('verifyFaceBtn');
    
    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw the video frame to the canvas
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert canvas to data URL and set to image
    const dataUrl = canvas.toDataURL('image/jpeg');
    capturedPhoto.src = dataUrl;
    
    // Show captured photo container
    capturedContainer.style.display = 'block';
    
    // Enable the verify button
    verifyBtn.disabled = false;
    
    // Convert data URL to Blob for API call
    capturedPhotoBlob = dataURItoBlob(dataUrl);
    
    addLogEntry('Photo captured successfully', 'info');
}

// Convert data URI to Blob
function dataURItoBlob(dataURI) {
    // Convert base64/URLEncoded data component to raw binary data
    let byteString;
    if (dataURI.split(',')[0].indexOf('base64') >= 0) {
        byteString = atob(dataURI.split(',')[1]);
    } else {
        byteString = decodeURIComponent(dataURI.split(',')[1]);
    }
    
    // Separate out the mime component
    const mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
    
    // Write the bytes of the string to a typed array
    const ia = new Uint8Array(byteString.length);
    for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }
    
    return new Blob([ia], { type: mimeString });
}

// Verify face and find matching rooms
export async function verifyFaceForRooms() {
    if (!capturedPhotoBlob) {
        showNotification('Please capture a photo first', 'warning');
        return;
    }
    
    const processingIndicator = document.getElementById('faceProcessingIndicator');
    const matchResults = document.getElementById('faceMatchResults');
    const availableRoomsContainer = document.getElementById('availableRoomsContainer');
    
    // Show processing indicator
    processingIndicator.style.display = 'flex';
    
    // Hide previous results
    matchResults.style.display = 'none';
    
    try {
        // Create form data with the captured photo
        const formData = new FormData();
        formData.append('file', capturedPhotoBlob, 'face.jpg');
        
        // Call API to verify face
        const response = await fetch('/api/verify-face-for-rooms', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // Hide processing indicator
        processingIndicator.style.display = 'none';
        
        if (data.status === 'success') {
            // Clear previous results
            availableRoomsContainer.innerHTML = '';
            
            if (data.authorized_rooms && data.authorized_rooms.length > 0) {
                // Create room cards for each authorized room
                data.authorized_rooms.forEach(room => {
                    const roomCard = document.createElement('div');
                    roomCard.className = 'card room-card';
                    roomCard.innerHTML = `
                        <div class="card-body">
                            <h6 class="card-title">Room ID: ${room.room_id.substring(0, 8)}...</h6>
                            <div class="d-flex justify-content-between">
                                <span class="text-muted">Max receivers: ${room.max_receivers > 0 ? room.max_receivers : 'Unlimited'}</span>
                                <button class="btn btn-sm btn-primary join-room-btn">Join Room</button>
                            </div>
                        </div>
                    `;
                    
                    // Add click event to join button
                    const joinBtn = roomCard.querySelector('.join-room-btn');
                    joinBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        joinRoomWithFaceAuth(room.room_id);
                    });
                    
                    // Add click event to entire card
                    roomCard.addEventListener('click', () => {
                        joinRoomWithFaceAuth(room.room_id);
                    });
                    
                    availableRoomsContainer.appendChild(roomCard);
                });
                
                // Show match results
                matchResults.style.display = 'block';
                
                addLogEntry(`Found ${data.authorized_rooms.length} rooms matching your face`, 'success');
                showNotification(`You are authorized for ${data.authorized_rooms.length} rooms`, 'success');
            } else {
                // No authorized rooms found
                availableRoomsContainer.innerHTML = `
                    <div class="alert alert-info">
                        <i class="bi bi-exclamation-circle me-2"></i>
                        No rooms found where your face is authorized.
                    </div>
                `;
                
                // Show match results (even if empty)
                matchResults.style.display = 'block';
                
                addLogEntry('No rooms match your face', 'info');
                showNotification('No authorized rooms found', 'info');
            }
        } else {
            showNotification('Error verifying face: ' + data.message, 'danger');
            addLogEntry('Face verification error: ' + data.message, 'error');
        }
    } catch (error) {
        // Hide processing indicator
        processingIndicator.style.display = 'none';
        
        showNotification('Error connecting to server: ' + error.message, 'danger');
        addLogEntry('Server connection error: ' + error.message, 'error');
    }
}

// Join a room using a face-authenticated room ID
function joinRoomWithFaceAuth(roomId) {
    // Set room ID in the direct key input
    document.getElementById('secretKey').value = roomId;
    
    // Call the joinRoomWithKey function
    joinRoomWithKey();
    
    // Stop camera after joining
    stopCamera();
}

// Preview uploaded face images for room creation
export function previewFaceImages() {
    const fileInput = document.getElementById('faceImages');
    const previewContainer = document.getElementById('facePreviewContainer');
    
    // Clear preview container
    previewContainer.innerHTML = '';
    
    if (fileInput.files.length > 0) {
        // Create image previews for each selected file
        Array.from(fileInput.files).forEach((file, index) => {
            // Skip non-image files
            if (!file.type.startsWith('image/')) {
                return;
            }
            
            // Create a URL for the image
            const imageUrl = URL.createObjectURL(file);
            
            // Create preview container
            const previewDiv = document.createElement('div');
            previewDiv.className = 'face-preview';
            previewDiv.innerHTML = `
                <img src="${imageUrl}" alt="Face preview ${index + 1}">
                <div class="remove-btn" data-index="${index}">
                    <i class="bi bi-x"></i>
                </div>
            `;
            
            previewContainer.appendChild(previewDiv);
        });
        
        // Add event listeners to remove buttons
        const removeButtons = document.querySelectorAll('.face-preview .remove-btn');
        removeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                // We can't actually remove files from a file input, so we'll hide the preview
                const previewElement = button.parentElement;
                previewElement.style.display = 'none';
            });
        });
    }
}