// roomJoining.js - Handles room joining and setup functionality
import { showNotification, addLogEntry } from './ui.js';
import { checkRoom, extractSecretKey, extractKeyFromImage } from './api.js';
import { connectWebSocket } from './websocket.js';
import { 
    setCurrentSecretKey, 
    setCurrentRole, 
    currentSecretKey, 
    stegoImageFilename 
} from './state.js';

// Automatically join a room with a key from URL
export async function autoJoinWithKey(secretKey) {
    if (!secretKey) return;
    
    try {
        const data = await checkRoom(secretKey);
        
        if (data.valid) {
            setCurrentSecretKey(secretKey);
            
            // Hide the initialOptions section when joining via URL
            document.getElementById('initialOptions').style.display = 'none';
            
            setupAsReceiver();
        } else {
            showNotification('Invalid secret key or nonexistent room.', 'danger');
        }
    } catch (error) {
        showNotification('An error occurred while joining room.', 'danger');
    }
}

// Join room with secret key
export async function joinRoomWithKey() {
    const secretKey = document.getElementById('secretKey').value.trim();
    
    if (!secretKey) {
        showNotification('Please enter a Secret Key', 'warning');
        return;
    }
    
    try {
        const data = await checkRoom(secretKey);
        
        if (data.valid) {
            setCurrentSecretKey(secretKey);
            setupAsReceiver();
        } else {
            showNotification('Invalid secret key or nonexistent room.', 'danger');
        }
    } catch (error) {
        showNotification('An error occurred while joining a room.', 'danger');
    }
}

// Extract key from encrypted message and join
export async function extractKeyAndJoin() {
    const encryptedText = document.getElementById('encryptedMessage').value.trim();
    
    if (!encryptedText) {
        showNotification('Please enter encrypted message', 'warning');
        return;
    }
    
    try {
        const data = await extractSecretKey(encryptedText);
        
        if (data.status === 'success') {
            setCurrentSecretKey(data.secret_key);
            
            // Add log entry about the extracted key
            addLogEntry(`Secret key extracted: ${data.secret_key}`, 'info');
            
            setupAsReceiver();
        } else {
            showNotification('Secret key could not be extracted: ' + data.message, 'danger');
        }
    } catch (error) {
        showNotification('An error occurred while extracting key', 'danger');
    }
}

// Extract key from image and join
export async function extractKeyFromImageAndJoin() {
    const imageInput = document.getElementById('stegoImageUpload');
    
    if (!imageInput.files || imageInput.files.length === 0) {
        showNotification('Please choose image', 'warning');
        return;
    }
    
    try {
        // Show loading
        document.getElementById('image-tab').innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        const data = await extractKeyFromImage(imageInput.files[0]);
        
        // Reset loading
        document.getElementById('image-tab').textContent = 'Upload Image';
        
        if (data.status === 'success') {
            setCurrentSecretKey(data.secret_key);
            setupAsReceiver();
        } else {
            showNotification('Secret key could not be extracted: ' + data.message, 'danger');
        }
    } catch (error) {
        // Reset loading
        document.getElementById('image-tab').textContent = 'Upload Image';
        showNotification('An error occurred during secret key extraction.', 'danger');
    }
}

// Continue as sender after creating a room
export function continueAsSender() {
    // Get the current secret key - check for face auth room first
    const faceAuthKey = document.getElementById('faceAuthRoomKey');
    if (faceAuthKey && faceAuthKey.textContent) {
        setCurrentSecretKey(faceAuthKey.textContent);
    }
    
    // Set current role to sender
    setCurrentRole('sender');
    
    // Hide all room creation views
    document.getElementById('roomCreatedDirect').style.display = 'none';
    document.getElementById('roomCreatedStego').style.display = 'none';
    document.getElementById('roomCreatedImage').style.display = 'none';
    document.getElementById('roomCreatedEmail').style.display = 'none';
    document.getElementById('roomCreatedFace').style.display = 'none';
    
    // Show file transfer interface with sender options
    document.getElementById('fileTransfer').style.display = 'block';
    document.getElementById('senderInterface').style.display = 'block';
    document.getElementById('receiverInterface').style.display = 'none';
    
    // Hide P2P-specific elements
    const p2pModeNotice = document.getElementById('p2pModeNotice');
    if (p2pModeNotice) {
        p2pModeNotice.style.display = 'none';
    }
    
    // Hide P2P connection code container
    const p2pConnectionCodeContainer = document.getElementById('p2pConnectionCodeContainer');
    if (p2pConnectionCodeContainer) {
        p2pConnectionCodeContainer.style.display = 'none';
    }
    
    // Hide P2P status row for regular rooms (not P2P mode)
    document.getElementById('p2pStatusRow').style.display = 'none';
    
    // Connect WebSocket
    connectWebSocket('sender');
}

// Download steganographic image
export function downloadStegoImage() {
    if (stegoImageFilename) {
        window.open(`/api/download-stego-image/${stegoImageFilename}`, '_blank');
    }
}

// Setup as sender
export function setupAsSender() {
    setCurrentRole('sender');
    
    // Hide room creation views
    document.getElementById('roomCreatedDirect').style.display = 'none';
    document.getElementById('roomCreatedStego').style.display = 'none';
    document.getElementById('roomCreatedImage').style.display = 'none';
    document.getElementById('roomCreatedEmail').style.display = 'none';
    
    // Show file transfer interface with sender options
    document.getElementById('fileTransfer').style.display = 'block';
    document.getElementById('senderInterface').style.display = 'block';
    document.getElementById('receiverInterface').style.display = 'none';
    
    // Hide P2P status row for regular rooms (not P2P mode)
    document.getElementById('p2pStatusRow').style.display = 'none';
    
    // Connect WebSocket
    connectWebSocket('sender');
}

// Setup as receiver
export function setupAsReceiver() {
    setCurrentRole('receiver');
    
    // Hide join room view
    document.getElementById('joinRoomOptions').style.display = 'none';
    
    // Show file transfer interface with receiver options
    document.getElementById('fileTransfer').style.display = 'block';
    document.getElementById('senderInterface').style.display = 'none';
    document.getElementById('receiverInterface').style.display = 'block';
    
    // Hide P2P status row for regular rooms (not P2P mode)
    document.getElementById('p2pStatusRow').style.display = 'none';
    
    // Hide P2P-specific elements
    const p2pModeNotice = document.getElementById('p2pModeNotice');
    if (p2pModeNotice) {
        p2pModeNotice.style.display = 'none';
    }
    
    // Hide P2P connection code input container
    const connectionCodeInputContainer = document.getElementById('connectionCodeInputContainer');
    if (connectionCodeInputContainer) {
        connectionCodeInputContainer.style.display = 'none';
    }
    
    // Connect WebSocket
    connectWebSocket('receiver');
}

// Leave room function
export function leaveRoom() {
    import('./websocket.js').then(({ closeWebSocket }) => {
        closeWebSocket();
    });
    
    import('./state.js').then(({ resetState }) => {
        resetState();
    });
    
    // Reset UI elements
    document.getElementById('transferLogs').innerHTML = '';
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressBar').textContent = '0%';
    document.getElementById('transferProgress').style.display = 'none';
    document.getElementById('integrityResult').style.display = 'none';
    document.getElementById('downloadBtnContainer').style.display = 'none';
    document.getElementById('encryptionInfo').style.display = 'none';
    
    // Reset form fields
    import('./ui.js').then(({ resetAllForms }) => {
        resetAllForms();
    });
    
    // Go back to initial view
    document.getElementById('createRoomOptions').style.display = 'none';
    document.getElementById('joinRoomOptions').style.display = 'none';
    document.getElementById('roomCreatedDirect').style.display = 'none';
    document.getElementById('roomCreatedStego').style.display = 'none';
    document.getElementById('roomCreatedImage').style.display = 'none';
    document.getElementById('roomCreatedEmail').style.display = 'none';
    document.getElementById('fileTransfer').style.display = 'none';
    document.getElementById('initialOptions').style.display = 'block';
}