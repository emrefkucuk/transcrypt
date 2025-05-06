// api.js - Handles API calls to the server
import { showNotification } from './ui.js';
import { 
    setCurrentSecretKey, 
    setStegoImageFilename, 
    currentSecretKey,
    setApiFeatures,
    apiFeatures
} from './state.js';

// Check API status and available features
export async function checkApiStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.status === 'success') {
            // Store feature availability in state
            setApiFeatures(data.features);
            
            // Update UI based on silent mode and features
            if (data.silent_mode) {
                console.log('API running in silent mode - text steganography disabled');
                
                // Disable text steganography option
                const stegoOption = document.getElementById('stegoOption');
                const stegoCard = document.querySelector('div.card.option-card[onclick*="selectKeyOption(\'stego\')"');
                
                if (stegoOption) {
                    stegoOption.disabled = true;
                    stegoOption.checked = false;
                    
                    // Add a note about silent mode
                    const stegoLabel = document.querySelector('label[for="stegoOption"]');
                    if (stegoLabel) {
                        // Find the h5 element within the stegoLabel
                        const stegoTitleElement = stegoLabel.querySelector('h5');
                        if (stegoTitleElement) {
                            stegoTitleElement.innerHTML += ' <span class="text-muted">(Disabled)</span>';
                        } else {
                            stegoLabel.innerHTML += ' <span class="text-muted">(Disabled in silent mode)</span>';
                        }
                    }
                    
                    // Make the entire card appear disabled
                    if (stegoCard) {
                        stegoCard.classList.add('disabled-card');
                        stegoCard.style.opacity = '0.6';
                        stegoCard.style.cursor = 'not-allowed';
                        
                        // Remove the onclick attribute to prevent clicking
                        stegoCard.removeAttribute('onclick');
                        
                        // Add a data attribute to mark as disabled
                        stegoCard.setAttribute('data-disabled', 'true');
                    }
                    
                    // Hide text steganography section completely
                    const stegoSection = document.getElementById('stegoSection');
                    if (stegoSection) {
                        stegoSection.style.display = 'none';
                    }
                }
                
                // ALSO DISABLE FACE AUTH
                const faceOption = document.getElementById('faceOption');
                if (faceOption) faceOption.disabled = true;
                
                const faceCard = document.querySelector('.card.option-card[onclick*="face"]') ||
                                document.querySelector('.card.option-card:has(#faceOption)');
                const faceLabel = faceCard?.querySelector('h5');
                
                if (faceLabel) {
                    faceLabel.innerHTML += ' <span class="text-muted">(Disabled)</span>';
                }
                
                // Make the face auth card appear disabled
                if (faceCard) {
                    faceCard.classList.add('disabled-card');
                    faceCard.style.opacity = '0.6';
                    faceCard.style.cursor = 'not-allowed';
                    
                    // Remove the onclick attribute to prevent clicking
                    faceCard.removeAttribute('onclick');
                    
                    // Add a data attribute to mark as disabled
                    faceCard.setAttribute('data-disabled', 'true');
                }
                
                // Hide face auth container completely
                const faceAuthContainer = document.getElementById('faceAuthContainer');
                if (faceAuthContainer) {
                    faceAuthContainer.style.display = 'none';
                }
                
                // DISABLE JOIN ROOM TABS FOR STEGANOGRAPHY AND FACE AUTH
                // Disable "Enter Hidden Message" tab in Join Room menu
                const encryptedTab = document.getElementById('encrypted-tab');
                if (encryptedTab) {
                    encryptedTab.classList.add('disabled');
                    encryptedTab.style.opacity = '0.6';
                    encryptedTab.style.cursor = 'not-allowed';
                    encryptedTab.tabIndex = -1;
                    encryptedTab.setAttribute('data-bs-toggle', '');
                }
                
                // Disable "Face Authentication" tab in Join Room menu
                const faceTab = document.getElementById('face-tab');
                if (faceTab) {
                    faceTab.classList.add('disabled');
                    faceTab.style.opacity = '0.6';
                    faceTab.style.cursor = 'not-allowed';
                    faceTab.tabIndex = -1;
                    faceTab.setAttribute('data-bs-toggle', '');
                }
                
                // Check all radio options and select a valid one if needed
                const directOption = document.getElementById('directOption');
                if (directOption) directOption.click();
            }
            
            return data;
        }
    } catch (error) {
        console.error('Error checking API status:', error);
    }
    
    return null;
}

// Load available models for steganography
export async function loadAvailableModels() {
    try {
        const response = await fetch('/api/get-available-models');
        const data = await response.json();
        
        if (data.status === 'success' && data.models) {
            // Populate model select dropdowns
            const modelSelect = document.getElementById('modelSelect');
            const regenerateModel = document.getElementById('regenerateModel');
            
            // Clear existing options
            modelSelect.innerHTML = '';
            regenerateModel.innerHTML = '';
            
            // Add models to dropdowns
            Object.entries(data.models).forEach(([id, name]) => {
                const option1 = new Option(name, id);
                const option2 = new Option(name, id);
                
                modelSelect.appendChild(option1);
                regenerateModel.appendChild(option2);
            });
        }
    } catch (error) {
        // Handle error silently
        console.error('Error loading models:', error);
    }
}

// Create a new room
export async function createRoom() {
    const useSteganography = document.getElementById('stegoOption').checked;
    const useImageSteganography = document.getElementById('imageOption').checked;
    const useEmail = document.getElementById('emailOption').checked;
    const useFaceAuth = document.getElementById('faceOption').checked;
    
    // Get maximum receivers setting
    const maxReceivers = document.getElementById('maxReceivers').value;
    
    try {
        // Show loading indicator
        document.getElementById('generatingIndicator').classList.add('show');
        document.getElementById('createRoomBtn').disabled = true;
        
        if (useImageSteganography) {
            return await createImageStegoRoom(maxReceivers);
        } else if (useSteganography) {
            return await createStegoRoom(maxReceivers);
        } else if (useEmail) {
            return await createEmailRoom(maxReceivers);
        } else if (useFaceAuth) {
            return await createFaceAuthRoom(document.getElementById('faceImages').files, maxReceivers);
        } else {
            return await createDirectRoom(maxReceivers);
        }
    } catch (error) {
        document.getElementById('generatingIndicator').classList.remove('show');
        document.getElementById('createRoomBtn').disabled = false;
        showNotification('An error occurred during room creation.', 'danger');
        return { status: 'error', message: error.message };
    }
}

// Create a room with image steganography
async function createImageStegoRoom(maxReceivers) {
    // Get the selected image file
    const imageInput = document.getElementById('stegoImage');
    const imageFile = imageInput.files[0];
    
    if (!imageFile) {
        showNotification('Please choose an image', 'warning');
        document.getElementById('generatingIndicator').classList.remove('show');
        document.getElementById('createRoomBtn').disabled = false;
        return { status: 'error', message: 'No image selected' };
    }
    
    // Check if the file is an image
    if (!imageFile.type.startsWith('image/')) {
        showNotification('Please choose a valid image!', 'warning');
        document.getElementById('generatingIndicator').classList.remove('show');
        document.getElementById('createRoomBtn').disabled = false;
        return { status: 'error', message: 'Invalid image format' };
    }
    
    // Create FormData to send the image
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('max_receivers', maxReceivers);
    
    // Create image stego room
    const response = await fetch('/api/create-image-stego-room', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    
    // Hide loading indicator
    document.getElementById('generatingIndicator').classList.remove('show');
    document.getElementById('createRoomBtn').disabled = false;
    
    if (data.status === 'success') {
        setCurrentSecretKey(data.secret_key);
        setStegoImageFilename(data.stego_image);
        
        // Load the steganographic image preview
        document.getElementById('stegoImagePreview').src = `/api/download-stego-image/${data.stego_image}`;
        
        // Show image stego room created view
        document.getElementById('createRoomOptions').style.display = 'none';
        document.getElementById('roomCreatedImage').style.display = 'block';
    } else {
        showNotification('Room creation failed: ' + data.message, 'danger');
    }
    
    return data;
}

// Create a room with text steganography
async function createStegoRoom(maxReceivers) {
    // Get prompt if provided
    const prompt = document.getElementById('stegoPrompt').value.trim();
    const model = document.getElementById('modelSelect').value;
    
    // Create steganographic room
    const response = await fetch('/api/create-steganographic-room', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            prompt: prompt || undefined,
            model: model,
            max_receivers: parseInt(maxReceivers)
        })
    });
    
    const data = await response.json();
    
    // Hide loading indicator
    document.getElementById('generatingIndicator').classList.remove('show');
    document.getElementById('createRoomBtn').disabled = false;
    
    if (data.status === 'success') {
        setCurrentSecretKey(data.secret_key);
        document.getElementById('stegoMessage').value = data.invitation_text;
        
        // Show stego room created view
        document.getElementById('createRoomOptions').style.display = 'none';
        document.getElementById('roomCreatedStego').style.display = 'block';
    } else {
        showNotification('Room creation failed: ' + data.message, 'danger');
    }
    
    return data;
}

// Create a room with email
async function createEmailRoom(maxReceivers) {
    // Get email details
    const senderEmail = document.getElementById('senderEmail').value.trim();
    const appPassword = document.getElementById('appPassword').value.trim();
    const receiverEmail = document.getElementById('receiverEmail').value.trim();
    const allowMultipleConnections = document.getElementById('allowMultipleConnections').checked;
    
    if (!senderEmail || !appPassword || !receiverEmail) {
        showNotification('Please fill all fields.', 'warning');
        document.getElementById('generatingIndicator').classList.remove('show');
        document.getElementById('createRoomBtn').disabled = false;
        return { status: 'error', message: 'Missing required fields' };
    }
    
    // Create email room
    const response = await fetch('/api/create-email-room', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            sender_email: senderEmail,
            sender_password: appPassword,
            recipient_email: receiverEmail,
            allow_multiple_connections: allowMultipleConnections,
            max_receivers: parseInt(maxReceivers)
        })
    });
    
    const data = await response.json();
    
    // Hide loading indicator
    document.getElementById('generatingIndicator').classList.remove('show');
    document.getElementById('createRoomBtn').disabled = false;
    
    if (data.status === 'success') {
        setCurrentSecretKey(data.secret_key);
        document.getElementById('emailSenderInfo').textContent = senderEmail;
        document.getElementById('emailReceiverInfo').textContent = receiverEmail;
        document.getElementById('emailLinkInfo').textContent = data.secure_link || data.invitation_link || '';
        
        // Show email room created view
        document.getElementById('createRoomOptions').style.display = 'none';
        document.getElementById('roomCreatedEmail').style.display = 'block';
    } else {
        showNotification('Room creation failed: ' + data.message, 'danger');
    }
    
    return data;
}

// Create a room with direct key
async function createDirectRoom(maxReceivers) {
    // Create direct key room
    const response = await fetch('/api/create-room', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            max_receivers: parseInt(maxReceivers)
        })
    });
    
    const data = await response.json();
    
    // Hide loading indicator
    document.getElementById('generatingIndicator').classList.remove('show');
    document.getElementById('createRoomBtn').disabled = false;
    
    if (data.status === 'success') {
        setCurrentSecretKey(data.secret_key);
        document.getElementById('generatedKey').textContent = data.secret_key;
        
        // Show direct room created view
        document.getElementById('createRoomOptions').style.display = 'none';
        document.getElementById('roomCreatedDirect').style.display = 'block';
    } else {
        showNotification('Room creation failed: ' + data.message, 'danger');
    }
    
    return data;
}

// Create a room with face authentication
export async function createFaceAuthRoom(files, maxReceivers) {
    const formData = new FormData();
    
    // Add each face image to the form data
    for (const file of files) {
        formData.append('files', file);
    }
    
    // Add max receivers parameter
    formData.append('max_receivers', maxReceivers);
    
    try {
        const response = await fetch('/api/create-face-auth-room', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // Hide loading indicator and enable button
        document.getElementById('generatingIndicator').classList.remove('show');
        document.getElementById('createRoomBtn').disabled = false;
        
        if (data.status === 'success') {
            // Update room details in the face auth room view
            document.getElementById('faceAuthRoomKey').textContent = data.secret_key;
            document.getElementById('faceAuthCount').textContent = data.faces_count || '0';
            
            // Display max receivers info (0 = unlimited)
            const maxReceivers = parseInt(data.max_receivers);
            document.getElementById('faceAuthMaxReceivers').textContent = 
                maxReceivers > 0 ? maxReceivers : 'Unlimited';
            
            // Hide creation options and show success view
            document.getElementById('createRoomOptions').style.display = 'none';
            document.getElementById('roomCreatedFace').style.display = 'block';
        }
        
        return data;
    } catch (error) {
        console.error('Error creating face auth room:', error);
        
        // Hide loading indicator and enable button in case of error
        document.getElementById('generatingIndicator').classList.remove('show');
        document.getElementById('createRoomBtn').disabled = false;
        
        return {
            status: 'error',
            message: `Network error: ${error.message}`
        };
    }
}

// Add additional authorized faces to an existing room
export async function addFacesToRoom(secretKey, files) {
    const formData = new FormData();
    
    // Add each face image to the form data
    for (const file of files) {
        formData.append('files', file);
    }
    
    // Add secret key parameter
    formData.append('secret_key', secretKey);
    
    try {
        const response = await fetch('/api/add-face-to-room', {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    } catch (error) {
        console.error('Error adding faces to room:', error);
        return {
            status: 'error',
            message: `Network error: ${error.message}`
        };
    }
}

// Check if a room exists
export async function checkRoom(secretKey) {
    try {
        const response = await fetch(`/api/check-room?secret_key=${encodeURIComponent(secretKey)}`);
        return await response.json();
    } catch (error) {
        return { valid: false, message: error.message };
    }
}

// Extract secret key from steganographic message
export async function extractSecretKey(encryptedText) {
    try {
        const response = await fetch('/api/extract-secret-key', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                invitation_text: encryptedText
            })
        });
        
        return await response.json();
    } catch (error) {
        return { status: 'error', message: error.message };
    }
}

// Extract secret key from image
export async function extractKeyFromImage(imageFile) {
    try {
        const formData = new FormData();
        formData.append('image', imageFile);
        
        const response = await fetch('/api/extract-key-from-image', {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    } catch (error) {
        return { status: 'error', message: error.message };
    }
}

// Regenerate steganographic text with the same key
export async function regenerateStegoText(prompt, model) {
    // When called from onclick attribute without parameters, get values from UI elements
    if (!prompt && !model) {
        prompt = document.getElementById('regeneratePrompt').value.trim();
        model = document.getElementById('regenerateModel').value;
        
        // Show regenerating indicator
        const regeneratingIndicator = document.getElementById('regeneratingIndicator');
        if (regeneratingIndicator) {
            regeneratingIndicator.style.display = 'flex';
        }
        
        // Disable the regenerate button
        const regenerateBtn = document.getElementById('regenerateBtn');
        if (regenerateBtn) {
            regenerateBtn.disabled = true;
        }
    }
    
    if (!currentSecretKey) {
        return { status: 'error', message: 'Secret key not available' };
    }
    
    try {
        const response = await fetch('/api/regenerate-steganographic-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                secret_key: currentSecretKey,
                prompt: prompt || undefined,
                model: model
            })
        });
        
        const data = await response.json();
        
        // When called from onclick handler, update UI with result
        if (!arguments.length) {
            // Hide regenerating indicator
            const regeneratingIndicator = document.getElementById('regeneratingIndicator');
            if (regeneratingIndicator) {
                regeneratingIndicator.style.display = 'none';
            }
            
            // Enable the regenerate button
            const regenerateBtn = document.getElementById('regenerateBtn');
            if (regenerateBtn) {
                regenerateBtn.disabled = false;
            }
            
            if (data.status === 'success') {
                // Update the stegoMessage textarea with the new text
                const stegoMessage = document.getElementById('stegoMessage');
                if (stegoMessage) {
                    stegoMessage.value = data.invitation_text;
                }
                
                showNotification('New message generated successfully!', 'success');
            } else {
                showNotification('Failed to generate new message: ' + data.message, 'danger');
            }
        }
        
        return data;
    } catch (error) {
        // Hide regenerating indicator and enable button when called directly
        if (!arguments.length) {
            const regeneratingIndicator = document.getElementById('regeneratingIndicator');
            if (regeneratingIndicator) {
                regeneratingIndicator.style.display = 'none';
            }
            
            const regenerateBtn = document.getElementById('regenerateBtn');
            if (regenerateBtn) {
                regenerateBtn.disabled = false;
            }
            
            showNotification('An error occurred: ' + error.message, 'danger');
        }
        
        return { status: 'error', message: error.message };
    }
}

// Process encrypted file with ChaCha20-Poly1305
export async function decryptChaCha(fileData, fileName, chachaKeyHex, nonceHex) {
    try {
        // Encode the filename to handle non-Latin characters
        const safeFileName = encodeURIComponent(fileName);
        
        const formData = new FormData();
        formData.append('file', new Blob([fileData]), safeFileName);
        formData.append('chacha_key', chachaKeyHex);
        formData.append('nonce', nonceHex);
        
        const response = await fetch('/api/decrypt-chacha', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Decryption server error:', errorText);
            throw new Error(`Server decryption failed: ${response.status} ${response.statusText}`);
        }
        
        return await response.blob();
    } catch (error) {
        console.error('ChaCha decryption error:', error);
        throw new Error('Decryption error: ' + error.message);
    }
}