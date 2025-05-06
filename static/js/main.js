// main.js - Entry point for the application
import { checkApiStatus, loadAvailableModels, createRoom, regenerateStegoText } from './api.js';
import { initializeTheme, toggleTheme } from './theme.js';
import { selectKeyOption, showCreateRoomOptions, showJoinRoomOptions, showP2POptions, goBack, copyToClipboard, selectP2PRole } from './ui.js';
import { showNotification, addLogEntry } from './ui.js';
import { previewFaceImages, startCamera, stopCamera, capturePhoto, verifyFaceForRooms } from './faceAuth.js';
import { leaveRoom, continueAsSender, joinRoomWithKey, downloadStegoImage, extractKeyAndJoin, extractKeyFromImageAndJoin, autoJoinWithKey } from './roomJoining.js';
import { sendFile, checkFileInputState } from './websocket.js';
import { downloadFile } from './encryption.js';
import { validateConnectionCode, isP2PConnected } from './p2p.js';

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    // Make UI functions available globally for onclick handlers
    window.showCreateRoomOptions = showCreateRoomOptions;
    window.showJoinRoomOptions = showJoinRoomOptions;
    window.showP2POptions = showP2POptions;
    window.selectKeyOption = selectKeyOption;
    window.goBack = goBack;
    window.startCamera = startCamera;
    window.capturePhoto = capturePhoto;
    window.verifyFaceForRooms = verifyFaceForRooms;
    window.createRoom = createRoom;
    window.leaveRoom = leaveRoom;
    window.continueAsSender = continueAsSender;
    window.sendFile = sendFile;
    window.downloadFile = downloadFile;
    window.copyToClipboard = copyToClipboard;
    window.joinRoomWithKey = joinRoomWithKey;
    window.downloadStegoImage = downloadStegoImage;
    window.extractKeyAndJoin = extractKeyAndJoin;
    window.extractKeyFromImageAndJoin = extractKeyFromImageAndJoin;
    window.regenerateStegoText = regenerateStegoText;
    window.validateConnectionCode = validateConnectionCode;
    window.toggleTheme = toggleTheme;
    window.selectP2PRole = selectP2PRole;
    window.checkFileInputState = checkFileInputState;
    
    // Check API status and availability
    await checkApiStatus();
    
    // Set up P2P connection code validation button if it exists
    const validateConnectionCodeBtn = document.getElementById('validateConnectionCodeBtn');
    if (validateConnectionCodeBtn) {
        validateConnectionCodeBtn.addEventListener('click', () => {
            const connectionCodeInput = document.getElementById('connectionCodeInput');
            if (connectionCodeInput) {
                validateConnectionCode(connectionCodeInput.value);
            }
        });
    }
    
    // Load available models if needed
    loadAvailableModels();
    
    // Initialize theme
    initializeTheme();
    
    // Set up theme toggle click handler
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Set up event listeners
    setupEventListeners();
    
    // Check URL parameters for room key and auto-join if found
    const urlParams = new URLSearchParams(window.location.search);
    const secretKey = urlParams.get('key');
    if (secretKey) {
        autoJoinWithKey(secretKey);
    }
});

// Set up event listeners
function setupEventListeners() {
    // Toggle password visibility in email setup
    const toggleBtn = document.getElementById('togglePassword');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const passwordInput = document.getElementById('appPassword');
            if (passwordInput) {
                const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
                passwordInput.setAttribute('type', type);
                toggleBtn.innerHTML = type === 'password' ? '<i class="bi bi-eye"></i>' : '<i class="bi bi-eye-slash"></i>';
            }
        });
    }
    
    // Face image preview for room creation
    const faceImages = document.getElementById('faceImages');
    if (faceImages) {
        faceImages.addEventListener('change', previewFaceImages);
    }
    
    // File input change event to update send button state
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            import('./state.js').then(({ setSelectedFile }) => {
                setSelectedFile(fileInput.files[0]);
                checkFileInputState();
                
                // Additional check for P2P mode
                import('./p2p.js').then(({ isP2PConnected, checkFileInputState: p2pCheckFileInputState }) => {
                    if (isP2PConnected()) {
                        p2pCheckFileInputState();
                    }
                });
            });
        });
    }
    
    // Face authentication webcam buttons
    const startCameraBtn = document.getElementById('startCameraBtn');
    if (startCameraBtn) {
        startCameraBtn.addEventListener('click', startCamera);
    }
    
    const capturePhotoBtn = document.getElementById('capturePhotoBtn');
    if (capturePhotoBtn) {
        capturePhotoBtn.addEventListener('click', capturePhoto);
    }
    
    const verifyFaceBtn = document.getElementById('verifyFaceBtn');
    if (verifyFaceBtn) {
        verifyFaceBtn.addEventListener('click', verifyFaceForRooms);
    }
    
    // Add tab change event listener
    const faceTabs = document.querySelectorAll('button[data-bs-toggle="tab"]');
    faceTabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', (event) => {
            // Stop camera if we're switching away from the face auth tab
            if (event.relatedTarget && event.relatedTarget.id === 'face-tab') {
                stopCamera();
            }
        });
    });
}