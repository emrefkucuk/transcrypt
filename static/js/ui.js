// ui.js - Handles UI-related functions
import { currentSecretKey } from './state.js';
import { isP2PConnected } from './p2p.js';

// Show different sections of the interface
export function showCreateRoomOptions() {
    document.getElementById('initialOptions').style.display = 'none';
    document.getElementById('createRoomOptions').style.display = 'block';
}

export function showJoinRoomOptions() {
    document.getElementById('initialOptions').style.display = 'none';
    document.getElementById('joinRoomOptions').style.display = 'block';
}

export function showP2POptions() {
    document.getElementById('initialOptions').style.display = 'none';
    document.getElementById('p2pRoleSelection').style.display = 'block';
}

// Function to handle P2P role selection
export function selectP2PRole(role) {
    // Hide the role selection
    document.getElementById('p2pRoleSelection').style.display = 'none';
    
    // Show the file transfer interface
    document.getElementById('fileTransfer').style.display = 'block';
    
    // Show the P2P status row
    document.getElementById('p2pStatusRow').style.display = 'block';
    
    // Add special P2P mode notice
    let p2pModeNotice = document.getElementById('p2pModeNotice');
    if (!p2pModeNotice) {
        p2pModeNotice = document.createElement('div');
        p2pModeNotice.id = 'p2pModeNotice';
        p2pModeNotice.className = 'alert alert-info';
        p2pModeNotice.innerHTML = '<i class="bi bi-info-circle-fill me-2"></i> Direct P2P mode active. You can send and receive files directly between devices.';
        
        // Insert at the top of the file transfer card
        const cardBody = document.querySelector('#fileTransfer .card-body');
        if (cardBody) {
            cardBody.insertBefore(p2pModeNotice, cardBody.firstChild);
        }
    } else {
        p2pModeNotice.style.display = 'block';
    }
    
    // Set up the UI based on the selected role
    if (role === 'sender') {
        // Show the sender interface
        document.getElementById('senderInterface').style.display = 'block';
        document.getElementById('receiverInterface').style.display = 'none';
        
        // Show the connection code container for the sender
        document.getElementById('p2pConnectionCodeContainer').style.display = 'block';
        
        // Save the role in the state
        window.currentRole = 'sender';
        
        // Initialize P2P mode for sender
        import('./p2p.js').then(({ initP2PWithCode, checkFileInputState }) => {
            initP2PWithCode('sender', null);
            
            // Add event listener to file input for P2P mode
            const fileInput = document.getElementById('fileInput');
            if (fileInput) {
                fileInput.addEventListener('change', () => {
                    checkFileInputState();
                });
            }
        });
        
        addLogEntry('P2P mode initialized as sender. Share your connection code with the receiver.', 'info');
    } else {
        // Show the receiver interface
        document.getElementById('senderInterface').style.display = 'none';
        document.getElementById('receiverInterface').style.display = 'block';
        
        // Show the connection code input for the receiver
        document.getElementById('connectionCodeInputContainer').style.display = 'block';
        
        // Save the role in the state
        window.currentRole = 'receiver';
        
        // Initialize P2P mode for receiver
        import('./p2p.js').then(({ initP2PWithCode }) => {
            initP2PWithCode('receiver', null);
        });
        
        addLogEntry('P2P mode initialized as receiver. Enter the connection code provided by the sender.', 'info');
    }
}

export function goBack() {
    // Reset form fields
    resetAllForms();

    // Hide all cards except initial options
    document.getElementById('createRoomOptions').style.display = 'none';
    document.getElementById('joinRoomOptions').style.display = 'none';
    document.getElementById('roomCreatedDirect').style.display = 'none';
    document.getElementById('roomCreatedStego').style.display = 'none';
    document.getElementById('roomCreatedImage').style.display = 'none';
    document.getElementById('roomCreatedEmail').style.display = 'none';
    document.getElementById('fileTransfer').style.display = 'none';
    document.getElementById('p2pRoleSelection').style.display = 'none'; // Hide P2P role selection
    document.getElementById('roomCreatedFace').style.display = 'none'; // Hide face auth room created view
    
    // Hide P2P specific UI elements
    const p2pModeNotice = document.getElementById('p2pModeNotice');
    if (p2pModeNotice) {
        p2pModeNotice.style.display = 'none';
    }
    
    // Hide P2P connection code container
    const p2pConnectionCodeContainer = document.getElementById('p2pConnectionCodeContainer');
    if (p2pConnectionCodeContainer) {
        p2pConnectionCodeContainer.style.display = 'none';
    }
    
    // Hide P2P connection code input container
    const connectionCodeInputContainer = document.getElementById('connectionCodeInputContainer');
    if (connectionCodeInputContainer) {
        connectionCodeInputContainer.style.display = 'none';
    }
    
    // Hide P2P status row
    const p2pStatusRow = document.getElementById('p2pStatusRow');
    if (p2pStatusRow) {
        p2pStatusRow.style.display = 'none';
    }
    
    // Also close any P2P connections
    import('./p2p.js').then(({ closeP2PConnection }) => {
        closeP2PConnection();
    });
    
    // Show initial options
    document.getElementById('initialOptions').style.display = 'block';
    
    // Reset WebSocket if needed
    import('./websocket.js').then(({ closeWebSocket }) => {
        closeWebSocket();
    });
}

// Handle key sharing option selection
export function selectKeyOption(option) {
    // Check if the option is disabled in silent mode
    if (option === 'stego') {
        const stegoOption = document.getElementById('stegoOption');
        const stegoCard = document.querySelector('.card.option-card[data-disabled="true"]');
        
        // If the option or card is disabled, don't allow selection
        if ((stegoOption && stegoOption.disabled) || stegoCard) {
            // Show notification that this option is disabled in silent mode
            showNotification('Text steganography is disabled in silent mode', 'warning');
            return; // Exit early
        }
    }
    
    // Check if face auth option is disabled
    if (option === 'face') {
        const faceOption = document.getElementById('faceOption');
        const faceCard = document.querySelector('.card.option-card[onclick*="face"][data-disabled="true"]') ||
                         document.querySelector('.card.option-card:has(#faceOption)[data-disabled="true"]');
        
        // If the option or card is disabled, don't allow selection
        if ((faceOption && faceOption.disabled) || faceCard) {
            // Show notification that this option is disabled
            showNotification('Face authentication is disabled', 'warning');
            return; // Exit early
        }
    }
    
    // Reset previously selected options
    document.getElementById('directOption').checked = (option === 'direct');
    document.getElementById('stegoOption').checked = (option === 'stego');
    document.getElementById('imageOption').checked = (option === 'image');
    document.getElementById('emailOption').checked = (option === 'email');
    document.getElementById('faceOption').checked = (option === 'face');
    
    // Style selected cards
    document.querySelectorAll('.option-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Show/hide appropriate containers
    document.getElementById('stegoPromptContainer').style.display = 'none';
    document.getElementById('imageUploadContainer').style.display = 'none';
    document.getElementById('emailSetupContainer').style.display = 'none';
    document.getElementById('faceAuthContainer').style.display = 'none';
    
    // Find the correct card and add selected class
    // Use a safer method that doesn't rely on the onclick attribute
    if (option === 'direct') {
        const directCard = document.querySelector('.card.option-card[onclick*="direct"]') ||
                           document.querySelector('.card.option-card:has(#directOption)');
        if (directCard) directCard.classList.add('selected');
    } else if (option === 'stego') {
        const stegoCard = document.querySelector('.card.option-card[onclick*="stego"]') ||
                          document.querySelector('.card.option-card:has(#stegoOption)');
        if (stegoCard) stegoCard.classList.add('selected');
    } else if (option === 'image') {
        const imageCard = document.querySelector('.card.option-card[onclick*="image"]') ||
                          document.querySelector('.card.option-card:has(#imageOption)');
        if (imageCard) imageCard.classList.add('selected');
    } else if (option === 'email') {
        const emailCard = document.querySelector('.card.option-card[onclick*="email"]') ||
                          document.querySelector('.card.option-card:has(#emailOption)');
        if (emailCard) emailCard.classList.add('selected');
    } else if (option === 'face') {
        const faceCard = document.querySelector('.card.option-card[onclick*="face"]') ||
                          document.querySelector('.card.option-card:has(#faceOption)');
        if (faceCard) faceCard.classList.add('selected');
    }
    
    // Display the appropriate container based on the option
    if (option === 'stego') {
        document.getElementById('stegoPromptContainer').style.display = 'block';
    } else if (option === 'image') {
        document.getElementById('imageUploadContainer').style.display = 'block';
    } else if (option === 'email') {
        document.getElementById('emailSetupContainer').style.display = 'block';
    } else if (option === 'face') {
        document.getElementById('faceAuthContainer').style.display = 'block';
    }
}

// Handle face authentication key sharing option
export function selectFaceAuthOption() {
    // Hide other option containers
    document.getElementById('stegoPromptContainer').style.display = 'none';
    document.getElementById('imageUploadContainer').style.display = 'none';
    document.getElementById('emailSetupContainer').style.display = 'none';
    
    // Show face auth container
    document.getElementById('faceAuthContainer').style.display = 'block';
}

// Show custom alert/notification
export function showNotification(message, type = 'info') {
    // Create the notification element if it doesn't exist yet
    let notificationContainer = document.getElementById('notificationContainer');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notificationContainer';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '20px';
        notificationContainer.style.right = '20px';
        notificationContainer.style.zIndex = '9999';
        notificationContainer.style.maxWidth = '350px';
        document.body.appendChild(notificationContainer);
    }
    
    // Create the notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.style.marginBottom = '10px';
    notification.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
    
    // Add icon based on type
    let icon = '';
    switch (type) {
        case 'success': icon = '<i class="bi bi-check-circle-fill me-2"></i>'; break;
        case 'danger': icon = '<i class="bi bi-exclamation-triangle-fill me-2"></i>'; break;
        case 'warning': icon = '<i class="bi bi-exclamation-circle-fill me-2"></i>'; break;
        case 'info': 
        default: icon = '<i class="bi bi-info-circle-fill me-2"></i>'; break;
    }
    
    notification.innerHTML = `
        ${icon} ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add the notification to the container
    notificationContainer.appendChild(notification);
    
    // Initialize Bootstrap alert
    const bsAlert = new bootstrap.Alert(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        try {
            bsAlert.close();
            // Remove from DOM after animation completes
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 500);
        } catch (e) {
            // Just in case the element was already removed
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }
    }, 5000);
}

// Reset all form fields and settings
export function resetAllForms() {
    // Reset create room form fields
    if (document.getElementById('stegoPrompt')) {
        document.getElementById('stegoPrompt').value = '';
    }
    
    if (document.getElementById('regeneratePrompt')) {
        document.getElementById('regeneratePrompt').value = '';
    }

    // Reset file inputs (checking if they exist first)
    const fileInputs = ['stegoImage', 'stegoImageUpload', 'fileInput'];
    fileInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input && input.value) {
            input.value = '';
        }
    });
    
    // Reset email fields
    const textFields = ['senderEmail', 'appPassword', 'receiverEmail', 'secretKey', 'encryptedMessage'];
    textFields.forEach(id => {
        const field = document.getElementById(id);
        if (field) {
            field.value = '';
        }
    });
    
    // Reset dropdown selections
    if (document.getElementById('encryptionMethod')) {
        document.getElementById('encryptionMethod').selectedIndex = 0;
    }
    
    // Reset checkboxes
    if (document.getElementById('integrityCheck')) {
        document.getElementById('integrityCheck').checked = true;
    }

    // Reset number input
    if (document.getElementById('maxReceivers')) {
        document.getElementById('maxReceivers').value = '0';
    }
    
    // Set Direct option as selected by default
    if (document.getElementById('directOption')) {
        document.getElementById('directOption').checked = true;
        document.querySelectorAll('.option-card').forEach(card => {
            card.classList.remove('selected');
        });
        const directCard = document.querySelector('.card.option-card[onclick="selectKeyOption(\'direct\')"]');
        if (directCard) {
            directCard.classList.add('selected');
        }
    }
    
    // Hide conditional containers
    const containers = ['stegoPromptContainer', 'imageUploadContainer', 'emailSetupContainer'];
    containers.forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.style.display = 'none';
        }
    });

    // Reset room tabs to first tab
    const directTab = document.getElementById('direct-tab');
    if (directTab) {
        try {
            const tab = new bootstrap.Tab(directTab);
            tab.show();
        } catch (e) {
            // Handle any errors silently
        }
    }
}

// Display a styled error message
export function displayErrorMessage(message) {
    // Create an error alert if it doesn't exist yet
    let errorAlert = document.getElementById('errorAlert');
    if (!errorAlert) {
        errorAlert = document.createElement('div');
        errorAlert.id = 'errorAlert';
        errorAlert.className = 'alert alert-danger alert-dismissible fade show';
        errorAlert.innerHTML = `
            <strong><i class="bi bi-exclamation-triangle-fill"></i> Hata!</strong> 
            <span id="errorMessage"></span>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert the error alert at the top of the current view
        const currentView = document.querySelector('.card[style*="display: block"]');
        if (currentView) {
            currentView.querySelector('.card-body').prepend(errorAlert);
        } else {
            // Fallback - add to body
            document.body.prepend(errorAlert);
        }
    }
    
    // Set the error message
    document.getElementById('errorMessage').textContent = message;
    
    // Automatically hide after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(errorAlert);
        bsAlert.close();
    }, 5000);
}

// Add log entry
export function addLogEntry(message, type = 'info') {
    const logContainer = document.getElementById('transferLogs');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    
    // Add timestamp
    const now = new Date();
    const timestamp = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    
    entry.textContent = `[${timestamp}] ${message}`;
    logContainer.appendChild(entry);
    
    // Scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Copy content to clipboard
export function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    
    if (element.tagName === 'TEXTAREA') {
        navigator.clipboard.writeText(element.value)
            .then(() => {
                showNotification('Text copied to clipboard!', 'success');
            })
            .catch(err => {
                showNotification('Copying failed.', 'danger');
            });
    } else {
        navigator.clipboard.writeText(element.textContent)
            .then(() => {
                showNotification('Text copied to clipboard!', 'success');
            })
            .catch(err => {
                showNotification('Copying failed.', 'danger');
            });
    }
}

// Function to generate a random connection code
export function generateConnectionCode() {
    const code = Math.random().toString(36).substring(2, 8).toUpperCase();
    document.getElementById('connectionCodeDisplay').textContent = code;
    return code;
}

// Function to show the connection code input for the receiver
export function showConnectionCodeInput() {
    document.getElementById('connectionCodeInputContainer').style.display = 'block';
}

// Function to show the connection code container for the sender
export function showConnectionCodeContainer() {
    const container = document.getElementById('p2pConnectionCodeContainer');
    if (container) {
        container.style.display = 'block';
    }
}

// Function to hide the connection code container for the sender
export function hideConnectionCodeContainer() {
    const container = document.getElementById('p2pConnectionCodeContainer');
    if (container) {
        container.style.display = 'none';
    }
}

// Function to hide the connection code input for the receiver
export function hideConnectionCodeInput() {
    const container = document.getElementById('connectionCodeInputContainer');
    if (container) {
        container.style.display = 'none';
    }
}

// Update display for P2P connection status
export function updateP2PStatusDisplay(connected) {
    const statusIndicator = document.getElementById('p2pStatusIndicator');
    const statusText = document.getElementById('p2pStatus');
    const connectionStatus = document.getElementById('connectionStatus');
    
    if (statusIndicator && statusText) {
        if (connected) {
            // Update P2P status indicators
            statusIndicator.className = 'bi bi-check-circle-fill text-success';
            statusText.textContent = 'Connected';
            statusText.className = 'text-success';
            
            // Also update the main connection status
            if (connectionStatus) {
                connectionStatus.textContent = 'Connected (P2P)';
                connectionStatus.className = 'text-success';
            }
            
            // Hide the code input/display since connection is established
            hideConnectionCodeContainer();
            hideConnectionCodeInput();
        } else {
            // Update P2P status indicators to show disconnected
            statusIndicator.className = 'bi bi-x-circle-fill text-danger';
            statusText.textContent = 'Disconnected';
            statusText.className = 'text-danger';
            
            // Also update the main connection status
            if (connectionStatus) {
                connectionStatus.textContent = 'P2P mode (waiting for connection)';
            }
        }
    } else if (connectionStatus) {
        // If P2P status elements don't exist but we have connection status
        if (connected) {
            connectionStatus.textContent = 'Connected (P2P)';
            connectionStatus.className = 'text-success';
        } else {
            connectionStatus.textContent = 'P2P mode (waiting for connection)';
        }
    }
}

// Update P2P participant counts display when connection is established
export function updateP2PParticipantCounts() {
    const senderCountElement = document.getElementById('senderCount');
    const receiverCountElement = document.getElementById('receiverCount');
    
    if (senderCountElement && receiverCountElement) {
        // In P2P mode, we always have 1 sender and 1 receiver when connected
        if (isP2PConnected()) {
            senderCountElement.textContent = '1';
            receiverCountElement.textContent = '1';
        } else {
            // If not connected, reset counts
            senderCountElement.textContent = '0';
            receiverCountElement.textContent = '0';
        }
    }
}