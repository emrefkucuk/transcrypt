// events.js - Handles global event functions used in HTML
import { createRoom, regenerateStegoText, extractSecretKey, extractKeyFromImage } from './api.js';
import { showNotification, addLogEntry, selectKeyOption } from './ui.js';
import { setCurrentSecretKey, getStegoImageFilename, currentSecretKey } from './state.js';
import { connectToRoom } from './websocket.js';

// Called from HTML onclick attributes
window.createRoom = async function() {
    try {
        // Check if face authentication is selected but no images provided
        if (document.getElementById('faceOption').checked) {
            const faceImages = document.getElementById('faceImages').files;
            if (!faceImages || faceImages.length === 0) {
                showNotification('Please upload at least one face image', 'warning');
                return;
            }
        }
        
        const result = await createRoom();
        
        if (result.status === 'success') {
            setCurrentSecretKey(result.secret_key);
            
            // Handle result differently based on the authentication type
            const useSteganography = document.getElementById('stegoOption').checked;
            const useImageSteganography = document.getElementById('imageOption').checked;
            const useEmail = document.getElementById('emailOption').checked;
            const useFaceAuth = document.getElementById('faceOption').checked;
            
            document.getElementById('createRoomOptions').style.display = 'none';
            
            if (useFaceAuth) {
                // Display face authentication success screen
                document.getElementById('faceAuthRoomKey').textContent = result.secret_key;
                document.getElementById('faceAuthCount').textContent = result.faces_count || '0';
                
                // Display max receivers (0 = unlimited)
                const maxReceivers = parseInt(result.max_receivers);
                document.getElementById('faceAuthMaxReceivers').textContent = 
                    maxReceivers > 0 ? maxReceivers : 'Unlimited';
                
                document.getElementById('roomCreatedFace').style.display = 'block';
                
                addLogEntry(`Created room with face authentication. ${result.faces_count} faces authorized.`, 'success');
            } else if (useSteganography) {
                document.getElementById('stegoMessage').value = result.invitation_text;
                document.getElementById('roomCreatedStego').style.display = 'block';
            } else if (useImageSteganography) {
                document.getElementById('roomCreatedImage').style.display = 'block';
            } else if (useEmail) {
                document.getElementById('roomCreatedEmail').style.display = 'block';
            } else {
                // Direct room creation
                document.getElementById('generatedKey').textContent = result.secret_key;
                document.getElementById('roomCreatedDirect').style.display = 'block';
            }
            
            showNotification('Room created successfully!', 'success');
        } else {
            showNotification('Room creation failed: ' + result.message, 'danger');
        }
    } catch (error) {
        showNotification('An error occurred: ' + error.message, 'danger');
    } finally {
        document.getElementById('generatingIndicator').classList.remove('show');
        document.getElementById('createRoomBtn').disabled = false;
    }
};

// Add face authentication room created view to continueAsSender function
window.continueAsSender = function() {
    // Hide all room created views
    document.getElementById('roomCreatedDirect').style.display = 'none';
    document.getElementById('roomCreatedStego').style.display = 'none';
    document.getElementById('roomCreatedImage').style.display = 'none';
    document.getElementById('roomCreatedEmail').style.display = 'none';
    document.getElementById('roomCreatedFace').style.display = 'none';
    
    // Show the file transfer view
    document.getElementById('fileTransfer').style.display = 'block';
    
    // Set up the interface as a sender
    document.getElementById('senderInterface').style.display = 'block';
    document.getElementById('receiverInterface').style.display = 'none';
    
    // Set global role
    window.currentRole = 'sender';
    
    // Try to connect to the room
    if (currentSecretKey) {
        connectToRoom(currentSecretKey, 'sender');
    } else {
        showNotification('Secret key not found. Please try creating a room again.', 'danger');
    }
    
    // Monitor file input changes to enable/disable the send button
    document.getElementById('fileInput').addEventListener('change', checkFileInputState);
};

// Leave room
window.leaveRoom = function() {
    // Close WebSocket connection
    import('./websocket.js').then(({ closeWebSocket }) => {
        closeWebSocket();
    });
    
    // Reset UI state and go back to initial view
    goBack();
};

// Go back to initial options
window.goBack = function() {
    import('./ui.js').then(({ goBack }) => {
        goBack();
    });
};

// Copy text to clipboard
window.copyToClipboard = function(elementId) {
    import('./ui.js').then(({ copyToClipboard }) => {
        copyToClipboard(elementId);
    });
};

// Enable/disable the send button based on file selection
function checkFileInputState() {
    const fileInput = document.getElementById('fileInput');
    const sendFileBtn = document.getElementById('sendFileBtn');
    
    if (fileInput && sendFileBtn) {
        sendFileBtn.disabled = !fileInput.files.length;
    }
}

// Download steganographic image
window.downloadStegoImage = function() {
    const filename = getStegoImageFilename();
    if (!filename) {
        showNotification('Image is not available', 'danger');
        return;
    }
    
    const link = document.createElement('a');
    link.href = `/api/download-stego-image/${filename}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};

// Select key sharing option
window.selectKeyOption = function(option) {
    import('./ui.js').then(({ selectKeyOption }) => {
        selectKeyOption(option);
    });
};

// Join room with secret key
window.joinRoomWithKey = async function() {
    const secretKey = document.getElementById('secretKey').value.trim();
    
    if (!secretKey) {
        showNotification('Please enter a secret key', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/check-room?secret_key=${encodeURIComponent(secretKey)}`);
        const data = await response.json();
        
        if (data.valid) {
            setCurrentSecretKey(secretKey);
            
            // Hide join options view
            document.getElementById('joinRoomOptions').style.display = 'none';
            
            // Show file transfer view
            document.getElementById('fileTransfer').style.display = 'block';
            
            // Set up as receiver
            document.getElementById('senderInterface').style.display = 'none';
            document.getElementById('receiverInterface').style.display = 'block';
            
            // Set global role
            window.currentRole = 'receiver';
            
            // Connect to the room
            connectToRoom(secretKey, 'receiver');
            
            showNotification('Joined room successfully!', 'success');
        } else {
            showNotification('Invalid secret key', 'danger');
        }
    } catch (error) {
        showNotification('Error connecting to room: ' + error.message, 'danger');
    }
};

// Extract key from steganographic text and join
window.extractKeyAndJoin = async function() {
    const encryptedMessage = document.getElementById('encryptedMessage').value.trim();
    
    if (!encryptedMessage) {
        showNotification('Please enter the steganographic message', 'warning');
        return;
    }
    
    try {
        const result = await extractSecretKey(encryptedMessage);
        
        if (result.status === 'success') {
            // Auto-fill the secret key field
            document.getElementById('secretKey').value = result.secret_key;
            
            // Join the room
            joinRoomWithKey();
        } else {
            showNotification('Failed to extract key: ' + result.message, 'danger');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'danger');
    }
};

// Extract key from image and join
window.extractKeyFromImageAndJoin = async function() {
    const fileInput = document.getElementById('stegoImageUpload');
    
    if (!fileInput.files.length) {
        showNotification('Please select an image', 'warning');
        return;
    }
    
    const imageFile = fileInput.files[0];
    
    // Check if it's an image
    if (!imageFile.type.startsWith('image/')) {
        showNotification('Please select a valid image file', 'warning');
        return;
    }
    
    try {
        const result = await extractKeyFromImage(imageFile);
        
        if (result.status === 'success') {
            // Auto-fill the secret key field
            document.getElementById('secretKey').value = result.secret_key;
            
            // Join the room
            joinRoomWithKey();
        } else {
            showNotification('Failed to extract key: ' + result.message, 'danger');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'danger');
    }
};

// Regenerate steganographic text
window.regenerateStegoText = function() {
    regenerateStegoText();
};

// Handle webcam functions for face authentication
window.startCamera = function() {
    import('./faceAuth.js').then(({ startCamera }) => {
        startCamera();
    });
};

window.stopCamera = function() {
    import('./faceAuth.js').then(({ stopCamera }) => {
        stopCamera();
    });
};

window.capturePhoto = function() {
    import('./faceAuth.js').then(({ capturePhoto }) => {
        capturePhoto();
    });
};

window.verifyFaceForRooms = function() {
    import('./faceAuth.js').then(({ verifyFaceForRooms }) => {
        verifyFaceForRooms();
    });
};

// Send file function
window.sendFile = function() {
    import('./websocket.js').then(({ sendFile }) => {
        sendFile();
    });
};

// Show P2P options
window.showP2POptions = function() {
    import('./ui.js').then(({ showP2POptions }) => {
        showP2POptions();
    });
};

// Select P2P role
window.selectP2PRole = function(role) {
    import('./ui.js').then(({ selectP2PRole }) => {
        selectP2PRole(role);
    });
};

// Initialize the UI handlers when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Handle validation of connection code in P2P mode
    const validateConnectionCodeBtn = document.getElementById('validateConnectionCodeBtn');
    if (validateConnectionCodeBtn) {
        validateConnectionCodeBtn.addEventListener('click', () => {
            import('./p2p.js').then(({ validateConnectionCode }) => {
                validateConnectionCode();
            });
        });
    }
    
    // Handle Enter key press in connection code input
    const connectionCodeInput = document.getElementById('connectionCodeInput');
    if (connectionCodeInput) {
        connectionCodeInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                import('./p2p.js').then(({ validateConnectionCode }) => {
                    validateConnectionCode();
                });
            }
        });
    }
});