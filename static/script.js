// Global variables
let currentSecretKey = null;
let currentRole = null; // 'sender' or 'receiver'
let wsConnection = null;
let selectedFile = null;
let receivedFileData = null;
let receivedFileName = null;
let receivedFileBlob = null;
let receivedChunks = [];
let totalChunks = 0;
let encryptionMetadata = null;  // Store encryption metadata for decryption
let stegoImageFilename = null;  // Store filename for stego image

// Check if URL has key parameter on page load
document.addEventListener('DOMContentLoaded', function() {
    // Parse URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const keyParam = urlParams.get('key');
    
    // If key parameter exists, automatically join the room
    if (keyParam) {
        console.log('Key parameter detected:', keyParam);
        autoJoinWithKey(keyParam);
    }
});

// Function to automatically join room with key from URL
async function autoJoinWithKey(secretKey) {
    if (!secretKey) return;
    
    try {
        const response = await fetch(`/api/check-room?secret_key=${encodeURIComponent(secretKey)}`);
        const data = await response.json();
        
        if (data.valid) {
            currentSecretKey = secretKey;
            setupAsReceiver();
        } else {
            alert('Invalid secret key or nonexistent room.');
        }
    } catch (error) {
        console.error('Error joining room:', error);
        alert('An error occured while joining room.');
    }
}

// Show different sections of the interface
function showCreateRoomOptions() {
    document.getElementById('initialOptions').style.display = 'none';
    document.getElementById('createRoomOptions').style.display = 'block';
}

function showJoinRoomOptions() {
    document.getElementById('initialOptions').style.display = 'none';
    document.getElementById('joinRoomOptions').style.display = 'block';
}

function goBack() {
    // Hide all cards except initial options
    document.getElementById('createRoomOptions').style.display = 'none';
    document.getElementById('joinRoomOptions').style.display = 'none';
    document.getElementById('roomCreatedDirect').style.display = 'none';
    document.getElementById('roomCreatedStego').style.display = 'none';
    document.getElementById('roomCreatedImage').style.display = 'none';
    document.getElementById('roomCreatedEmail').style.display = 'none';
    document.getElementById('fileTransfer').style.display = 'none';
    
    // Show initial options
    document.getElementById('initialOptions').style.display = 'block';
    
    // Reset WebSocket if needed
    if (wsConnection) {
        wsConnection.close();
        wsConnection = null;
    }
}

// Handle key sharing option selection
function selectKeyOption(option) {
    // Update radio buttons
    document.getElementById('directOption').checked = (option === 'direct');
    document.getElementById('stegoOption').checked = (option === 'stego');
    document.getElementById('imageOption').checked = (option === 'image');
    document.getElementById('emailOption').checked = (option === 'email');
    
    // Style selected cards
    document.querySelectorAll('.option-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Show/hide appropriate containers
    document.getElementById('stegoPromptContainer').style.display = 'none';
    document.getElementById('imageUploadContainer').style.display = 'none';
    document.getElementById('emailSetupContainer').style.display = 'none';
    
    if (option === 'direct') {
        document.querySelector('.card.option-card[onclick="selectKeyOption(\'direct\')"]').classList.add('selected');
    } else if (option === 'stego') {
        document.querySelector('.card.option-card[onclick="selectKeyOption(\'stego\')"]').classList.add('selected');
        document.getElementById('stegoPromptContainer').style.display = 'block';
    } else if (option === 'image') {
        document.querySelector('.card.option-card[onclick="selectKeyOption(\'image\')"]').classList.add('selected');
        document.getElementById('imageUploadContainer').style.display = 'block';
    } else if (option === 'email') {
        document.querySelector('.card.option-card[onclick="selectKeyOption(\'email\')"]').classList.add('selected');
        document.getElementById('emailSetupContainer').style.display = 'block';
    }
}

// Create room function
async function createRoom() {
    const useSteganography = document.getElementById('stegoOption').checked;
    const useImageSteganography = document.getElementById('imageOption').checked;
    const useEmail = document.getElementById('emailOption').checked;
    
    // Get maximum receivers setting
    const maxReceivers = document.getElementById('maxReceivers').value;
    
    try {
        // Show loading indicator
        document.getElementById('generatingIndicator').classList.add('show');
        document.getElementById('createRoomBtn').disabled = true;
        
        if (useImageSteganography) {
            // Get the selected image file
            const imageInput = document.getElementById('stegoImage');
            const imageFile = imageInput.files[0];
            
            if (!imageFile) {
                alert('Please choose an image');
                document.getElementById('generatingIndicator').classList.remove('show');
                document.getElementById('createRoomBtn').disabled = false;
                return;
            }
            
            // Check if the file is an image
            if (!imageFile.type.startsWith('image/')) {
                alert('Please choose a valid image!');
                document.getElementById('generatingIndicator').classList.remove('show');
                document.getElementById('createRoomBtn').disabled = false;
                return;
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
                currentSecretKey = data.secret_key;
                stegoImageFilename = data.stego_image;
                
                // Load the steganographic image preview
                document.getElementById('stegoImagePreview').src = `/api/download-stego-image/${stegoImageFilename}`;
                
                // Show image stego room created view
                document.getElementById('createRoomOptions').style.display = 'none';
                document.getElementById('roomCreatedImage').style.display = 'block';
            } else {
                alert('Room creation failed: ' + data.message);
            }
        } else if (useSteganography) {
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
                currentSecretKey = data.secret_key;
                document.getElementById('stegoMessage').value = data.invitation_text;
                
                // Show stego room created view
                document.getElementById('createRoomOptions').style.display = 'none';
                document.getElementById('roomCreatedStego').style.display = 'block';
            } else {
                alert('Room creation failed: ' + data.message);
            }
        } else if (useEmail) {
            // Get email details
            const senderEmail = document.getElementById('senderEmail').value.trim();
            const appPassword = document.getElementById('appPassword').value.trim();
            const receiverEmail = document.getElementById('receiverEmail').value.trim();
            
            if (!senderEmail || !appPassword || !receiverEmail) {
                alert('Please fill all fields.');
                document.getElementById('generatingIndicator').classList.remove('show');
                document.getElementById('createRoomBtn').disabled = false;
                return;
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
                    max_receivers: parseInt(maxReceivers)
                })
            });
            
            const data = await response.json();
            
            // Hide loading indicator
            document.getElementById('generatingIndicator').classList.remove('show');
            document.getElementById('createRoomBtn').disabled = false;
            
            if (data.status === 'success') {
                currentSecretKey = data.secret_key;
                document.getElementById('emailSenderInfo').textContent = senderEmail;
                document.getElementById('emailReceiverInfo').textContent = receiverEmail;
                document.getElementById('emailLinkInfo').textContent = data.secure_link || data.invitation_link || '';
                
                // Show email room created view
                document.getElementById('createRoomOptions').style.display = 'none';
                document.getElementById('roomCreatedEmail').style.display = 'block';
            } else {
                alert('Room creation failed: ' + data.message);
            }
        } else {
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
                currentSecretKey = data.secret_key;
                document.getElementById('generatedKey').textContent = data.secret_key;
                
                // Show direct room created view
                document.getElementById('createRoomOptions').style.display = 'none';
                document.getElementById('roomCreatedDirect').style.display = 'block';
            } else {
                alert('Room creation failed: ' + data.message);
            }
        }
    } catch (error) {
        console.error('Error creating room:', error);
        document.getElementById('generatingIndicator').classList.remove('show');
        document.getElementById('createRoomBtn').disabled = false;
        alert('An error occured during room creation.');
    }
}

// Join room with secret key
async function joinRoomWithKey() {
    const secretKey = document.getElementById('secretKey').value.trim();
    
    if (!secretKey) {
        alert('Please enter a Secret Key');
        return;
    }
    
    try {
        const response = await fetch(`/api/check-room?secret_key=${encodeURIComponent(secretKey)}`);
        const data = await response.json();
        
        if (data.valid) {
            currentSecretKey = secretKey;
            setupAsReceiver();
        } else {
            alert('Invalid secret key or nonexistent room.');
        }
    } catch (error) {
        console.error('Error joining room:', error);
        alert('An error occured while joining a room.');
    }
}

// Extract key from encrypted message and join
async function extractKeyAndJoin() {
    const encryptedText = document.getElementById('encryptedMessage').value.trim();
    
    if (!encryptedText) {
        alert('Please enter encrypted message');
        return;
    }
    
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
        
        const data = await response.json();
        
        if (data.status === 'success') {
            currentSecretKey = data.secret_key;
            setupAsReceiver();
        } else {
            alert('Secret key could not be extracted: ' + data.message);
        }
    } catch (error) {
        console.error('Error extracting key:', error);
        alert('An error occured while extracting key');
    }
}

// Extract key from image and join
async function extractKeyFromImageAndJoin() {
    const imageInput = document.getElementById('stegoImageUpload');
    
    if (!imageInput.files || imageInput.files.length === 0) {
        alert('Please choose image');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('image', imageInput.files[0]);
        
        // Show loading
        document.getElementById('image-tab').innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        const response = await fetch('/api/extract-key-from-image', {
            method: 'POST',
            body: formData
        });
        
        // Reset loading
        document.getElementById('image-tab').textContent = 'Upload Image';
        
        const data = await response.json();
        
        if (data.status === 'success') {
            currentSecretKey = data.secret_key;
            setupAsReceiver();
        } else {
            alert('Secret key could not be extracted: ' + data.message);
        }
    } catch (error) {
        // Reset loading
        document.getElementById('image-tab').textContent = 'Upload Image';
        console.error('Error extracting key from image:', error);
        alert('An error occured during secret key extraction.');
    }
}

// Continue as sender after creating a room
function continueAsSender() {
    setupAsSender();
}

// Download steganographic image
function downloadStegoImage() {
    if (stegoImageFilename) {
        window.open(`/api/download-stego-image/${stegoImageFilename}`, '_blank');
    }
}

// Setup as sender
function setupAsSender() {
    currentRole = 'sender';
    
    // Hide room creation views
    document.getElementById('roomCreatedDirect').style.display = 'none';
    document.getElementById('roomCreatedStego').style.display = 'none';
    document.getElementById('roomCreatedImage').style.display = 'none';
    document.getElementById('roomCreatedEmail').style.display = 'none';
    
    // Show file transfer interface with sender options
    document.getElementById('fileTransfer').style.display = 'block';
    document.getElementById('senderInterface').style.display = 'block';
    document.getElementById('receiverInterface').style.display = 'none';
    
    // Connect WebSocket
    connectWebSocket('sender');
}

// Setup as receiver
function setupAsReceiver() {
    currentRole = 'receiver';
    
    // Hide join room view
    document.getElementById('joinRoomOptions').style.display = 'none';
    
    // Show file transfer interface with receiver options
    document.getElementById('fileTransfer').style.display = 'block';
    document.getElementById('senderInterface').style.display = 'none';
    document.getElementById('receiverInterface').style.display = 'block';
    
    // Connect WebSocket
    connectWebSocket('receiver');
}

// Connect to WebSocket
function connectWebSocket(role) {
    if (wsConnection) {
        wsConnection.close();
    }
    
    const connectionStatus = document.getElementById('connectionStatus');
    connectionStatus.textContent = 'Connecting...';
    
    // Create WebSocket connection
    wsConnection = new WebSocket(`ws://${window.location.host}/ws/${role}/${currentSecretKey}`);
    
    wsConnection.onopen = () => {
        connectionStatus.textContent = 'Connected';
        addLogEntry('Connected to server', 'info');
        
        if (role === 'sender') {
            checkFileInputState();
        }
    };
    
    wsConnection.onclose = (event) => {
        connectionStatus.textContent = 'Connection lost';
        
        // Check if this was an abnormal closure with a reason
        if (event.code === 1000) {
            // Normal closure
            addLogEntry('Connection to server lost', 'info');
        } else {
            // Abnormal closure
            addLogEntry('Connection to server lost: ' + (event.reason || 'Bilinmeyen hata'), 'error');
        }
        
        if (role === 'sender') {
            document.getElementById('sendFileBtn').disabled = true;
        }
    };
    
    wsConnection.onerror = (error) => {
        console.error('WebSocket error:', error);
        connectionStatus.textContent = 'Connnection error';
        addLogEntry('Connnection error', 'error');
    };
    
    wsConnection.onmessage = handleWebSocketMessage;
}

// Handle WebSocket messages
function handleWebSocketMessage(event) {
    try {
        if (typeof event.data === 'string') {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'status':
                    updateRoomStatus(data);
                    break;
                case 'transfer_start':
                    handleTransferStart(data);
                    break;
                case 'transfer_progress':
                    updateTransferProgress(data);
                    break;
                case 'transfer_complete':
                    handleTransferComplete(data);
                    break;
                case 'error':
                    handleErrorMessage(data);
                    break;
            }
        } else if (currentRole === 'receiver') {
            // Binary data - we now get a complete file at once, not chunks
            receivedFileBlob = new Blob([event.data]);
            addLogEntry('File received, processing...', 'info');
        }
    } catch (error) {
        console.error('Error processing WebSocket message:', error);
    }
}

// Handle error messages from the server
function handleErrorMessage(data) {
    // Log error
    addLogEntry(`Error: ${data.message}`, 'error');
    
    // Display the error using our new error display function
    displayErrorMessage(data.message);
    
    // If it's a room capacity error, go back to the join screen
    if (data.message.includes("maximum capacity")) {
        setTimeout(() => {
            // Disconnect websocket
            if (wsConnection) {
                wsConnection.close();
                wsConnection = null;
            }
            
            // If we're in receiver mode, go back to join options
            if (currentRole === 'receiver') {
                document.getElementById('fileTransfer').style.display = 'none';
                document.getElementById('joinRoomOptions').style.display = 'block';
            }
        }, 1000);
    }
}

// Update room status based on WebSocket message
function updateRoomStatus(data) {
    document.getElementById('senderCount').textContent = data.senders;
    document.getElementById('receiverCount').textContent = data.receivers;
    
    if (currentRole === 'sender') {
        document.getElementById('sendFileBtn').disabled = !data.ready_to_transfer;
        
        if (data.ready_to_transfer) {
            addLogEntry('Receiver ready, you may send a file', 'info');
        } else if (data.receivers === 0) {
            addLogEntry('Waiting for receiver connection', 'info');
        }
    }
}

// Handle the start of a file transfer
function handleTransferStart(data) {
    document.getElementById('transferProgress').style.display = 'block';
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressBar').textContent = '0%';
    
    if (currentRole === 'receiver') {
        // Reset variables
        receivedFileBlob = null;
        encryptionMetadata = null;
        receivedFileName = data.filename;
        
        document.getElementById('fileInfo').textContent = 
            `Receiving file: ${data.filename} (${formatFileSize(data.filesize)})`;
        
        addLogEntry(`File transfer started: ${data.filename}`, 'info');
        
        // Show encryption information if available
        if (data.encryptionOptions) {
            document.getElementById('encryptionInfo').style.display = 'block';
            
            let methodText = 'Encryption: ';
            if (data.encryptionOptions.method === 'aes-256-gcm') {
                methodText += 'AES-256-GCM';
                addLogEntry('File is encrypted with AES-256-GCM', 'info');
            } else {
                methodText += 'No Encryption';
                addLogEntry('File sending without encryption', 'info');
            }
            document.getElementById('encryptionMethodInfo').textContent = methodText;
            
            let integrityText = 'Integrity Validation: ';
            if (data.encryptionOptions.integrityCheck) {
                integrityText += 'Active (SHA-256)';
                addLogEntry('SHA-256 integrity validation active', 'info');
            } else {
                integrityText += 'Passive';
                addLogEntry('Integrity validation inactive', 'warning');
            }
            document.getElementById('integrityCheckInfo').textContent = integrityText;
        }
    } else {
        document.getElementById('fileInfo').textContent = 
            `Sending file: ${data.filename} (${formatFileSize(data.filesize)})`;
        
        addLogEntry(`File transfer started: ${data.filename}`, 'info');
    }
}

// Update transfer progress
function updateTransferProgress(data) {
    const percentage = data.percentage;
    document.getElementById('progressBar').style.width = `${percentage}%`;
    document.getElementById('progressBar').textContent = `${percentage}%`;
    
    // Store encryption metadata for decryption
    if (currentRole === 'receiver' && data.encryption_metadata) {
        encryptionMetadata = data.encryption_metadata;
        
        if (data.encryption_metadata.aes_key) {
            addLogEntry('Keys received', 'info');
        }
        
        if (data.encryption_metadata.file_hash) {
            addLogEntry('Hash value received', 'info');
        }
    }
}

// Handle completed transfer
function handleTransferComplete(data) {
    addLogEntry('File transfer successful', 'success');
    
    if (currentRole === 'receiver') {
        receivedFileName = data.filename;
        
        // Process the received file if it's encrypted
        if (encryptionMetadata && encryptionMetadata.aes_key) {
            processEncryptedFile();
        } else {
            // If not encrypted, show the download button
            document.getElementById('downloadBtnContainer').style.display = 'block';
        }
        
        // Show integrity verification result if available
        if (data.integrity_verified !== undefined) {
            const resultElement = document.getElementById('integrityResult');
            const messageElement = document.getElementById('integrityMessage');
            
            resultElement.style.display = 'block';
            
            if (data.integrity_verified) {
                resultElement.className = 'integrity-result integrity-success';
                messageElement.innerHTML = '<i class="bi bi-check-circle-fill"></i> Integrity validated, you may download the file.';
                addLogEntry('Integrity validated', 'success');
            } else {
                resultElement.className = 'integrity-result integrity-error';
                messageElement.innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i> WARNING: Integrity validation failed! File may be tampered with.';
                addLogEntry('Integrity validation failed!', 'error');
            }
        }
    }
}

// Process encrypted file (decryption)
async function processEncryptedFile() {
    if (!receivedFileBlob || !encryptionMetadata) {
        addLogEntry('File could not be processed: Missing data', 'error');
        return;
    }
    
    try {
        addLogEntry('Decrypting file...', 'info');
        
        // Read file as ArrayBuffer
        const fileData = await receivedFileBlob.arrayBuffer();
        
        // Get encryption parameters
        const aesKeyHex = encryptionMetadata.aes_key;
        const ivHex = encryptionMetadata.iv;
        const tagHex = encryptionMetadata.tag;
        
        // Convert hex strings to Uint8Array
        const aesKey = hexToUint8Array(aesKeyHex);
        const iv = hexToUint8Array(ivHex);
        const tag = hexToUint8Array(tagHex);
        
        // Decrypt the file using WebCrypto API
        const decryptedData = await decryptFileWithAES(fileData, aesKey, iv, tag);
        
        // Create a blob from decrypted data
        receivedFileBlob = new Blob([decryptedData]);
        
        addLogEntry('Decryption successful!', 'success');
        
        // Show download button
        document.getElementById('downloadBtnContainer').style.display = 'block';
    } catch (error) {
        console.error('Decryption error:', error);
        addLogEntry('Error with decryption: ' + error.message, 'error');
    }
}

// Helper function to convert hex string to Uint8Array
function hexToUint8Array(hexString) {
    const bytes = new Uint8Array(hexString.length / 2);
    for (let i = 0; i < hexString.length; i += 2) {
        bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);
    }
    return bytes;
}

// Decrypt file with AES-GCM using WebCrypto API
async function decryptFileWithAES(encryptedData, aesKey, iv, tag) {
    try {
        // Import the AES key
        const key = await window.crypto.subtle.importKey(
            "raw",
            aesKey,
            { name: "AES-GCM" },
            false,
            ["decrypt"]
        );
        
        // In AES-GCM, the tag is usually appended to the end of the ciphertext
        // Create a new ArrayBuffer that combines the encryptedData and tag
        const combinedLength = encryptedData.byteLength + tag.byteLength;
        const combinedData = new Uint8Array(combinedLength);
        
        // Copy encrypted data first
        combinedData.set(new Uint8Array(encryptedData), 0);
        // Append the tag
        combinedData.set(tag, encryptedData.byteLength);
        
        // Decrypt the data
        const algorithm = {
            name: "AES-GCM",
            iv: iv,
            tagLength: 128 // 16 bytes (128 bits)
        };
        
        try {
            const decrypted = await window.crypto.subtle.decrypt(
                algorithm,
                key,
                combinedData
            );
            return decrypted;
        } catch (innerError) {
            console.error("First approach failed, trying alternate approach:", innerError);
            
            // Alternate approach - some implementations expect the tag separate from data
            // Try with just the encrypted data without the tag
            return await window.crypto.subtle.decrypt(
                algorithm,
                key,
                encryptedData
            );
        }
    } catch (error) {
        console.error("Decryption error:", error);
        throw new Error("Decryption failed: " + error.message);
    }
}

// Format file size for display
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' bytes';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    else return (bytes / 1073741824).toFixed(1) + ' GB';
}

// Handle file input changes
document.getElementById('fileInput').addEventListener('change', function(e) {
    selectedFile = e.target.files[0];
    checkFileInputState();
});

// Check if send button should be enabled
function checkFileInputState() {
    const sendBtn = document.getElementById('sendFileBtn');
    
    if (selectedFile && wsConnection && wsConnection.readyState === WebSocket.OPEN) {
        const receiverCount = parseInt(document.getElementById('receiverCount').textContent);
        
        if (receiverCount > 0) {
            sendBtn.disabled = false;
            return;
        }
    }
    
    sendBtn.disabled = true;
}

// Send file through WebSocket
function sendFile() {
    if (!selectedFile || !wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
        alert('File not selected or connection could not be established');
        return;
    }

    // Get encryption options
    const encryptionOptions = {
        method: document.getElementById('encryptionMethod').value,
        integrityCheck: document.getElementById('integrityCheck').checked
    };

    // Show progress UI
    document.getElementById('transferProgress').style.display = 'block';
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressBar').textContent = '0%';
    
    addLogEntry('Starting file transfer...', 'info');
    
    // Log encryption options
    if (encryptionOptions.method === 'aes-256-gcm') {
        addLogEntry('Dosya AES-256-GCM ile şifrelenecek', 'info');
    } else {
        addLogEntry('Dosya şifrelemesiz gönderilecek', 'info');
    }
    
    if (encryptionOptions.integrityCheck) {
        addLogEntry('SHA-256 bütünlük doğrulaması aktif', 'info');
    }

    // Send file metadata
    wsConnection.send(JSON.stringify({
        type: 'start_transfer',
        filename: selectedFile.name,
        filesize: selectedFile.size,
        encryptionOptions: encryptionOptions
    }));

    // Start reading and sending file chunks
    const chunkSize = 64 * 1024; // 64KB chunks
    const totalChunks = Math.ceil(selectedFile.size / chunkSize);
    let chunkId = 0;

    const reader = new FileReader();
    
    reader.onload = (e) => {
        if (wsConnection.readyState === WebSocket.OPEN) {
            // Send binary chunk
            wsConnection.send(e.target.result);
            
            // Send chunk metadata
            wsConnection.send(JSON.stringify({
                chunk_id: chunkId,
                total_chunks: totalChunks
            }));
            
            if (chunkId === 0) {
                addLogEntry('First file chunk sent', 'info');
            } else if (chunkId === totalChunks - 1) {
                addLogEntry('Last file chunk sent', 'info');
            }
            
            chunkId++;
            
            if (chunkId < totalChunks) {
                // Read next chunk
                const start = chunkId * chunkSize;
                const end = Math.min(start + chunkSize, selectedFile.size);
                readNextChunk(start, end);
            }
        }
    };
    
    const readNextChunk = (start, end) => {
        const slice = selectedFile.slice(start, end);
        reader.readAsArrayBuffer(slice);
    };
    
    // Start reading first chunk
    readNextChunk(0, chunkSize);
}

// Download received file
function downloadFile() {
    if (!receivedFileBlob || !receivedFileName) {
        addLogEntry('İndirilecek dosya bulunamadı', 'error');
        return;
    }

    const url = URL.createObjectURL(receivedFileBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = receivedFileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    addLogEntry(`File is downloaded as "${receivedFileName}"`, 'success');
}

// Leave room function
function leaveRoom() {
    if (wsConnection) {
        wsConnection.close();
        wsConnection = null;
    }
    
    // Reset variables
    currentSecretKey = null;
    currentRole = null;
    selectedFile = null;
    receivedFileBlob = null;
    receivedFileName = null;
    receivedChunks = [];
    
    // Reset UI elements
    document.getElementById('transferLogs').innerHTML = '';
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressBar').textContent = '0%';
    document.getElementById('transferProgress').style.display = 'none';
    document.getElementById('integrityResult').style.display = 'none';
    document.getElementById('downloadBtnContainer').style.display = 'none';
    document.getElementById('encryptionInfo').style.display = 'none';
    
    // Go back to initial view
    goBack();
}

// Add log entry
function addLogEntry(message, type = 'info') {
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
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    
    if (element.tagName === 'TEXTAREA') {
        navigator.clipboard.writeText(element.value)
            .then(() => {
                alert('Text copied to clipboard!');
            })
            .catch(err => {
                console.error('Copy error:', err);
                alert('Copying failed.');
            });
    } else {
        navigator.clipboard.writeText(element.textContent)
            .then(() => {
                alert('Text copied to clipboard!');
            })
            .catch(err => {
                console.error('Copying failed.:', err);
                alert('Copying failed..');
            });
    }
}

// Regenerate steganographic text
async function regenerateStegoText() {
    if (!currentSecretKey) {
        alert('Secret key not available');
        return;
    }
    
    // Show loading indicator
    document.getElementById('regeneratingIndicator').classList.add('show');
    document.getElementById('regenerateBtn').disabled = true;
    
    try {
        // Get regeneration parameters
        const prompt = document.getElementById('regeneratePrompt').value.trim();
        const model = document.getElementById('regenerateModel').value;
        
        // Call API to regenerate text
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
        
        // Hide loading indicator
        document.getElementById('regeneratingIndicator').classList.remove('show');
        document.getElementById('regenerateBtn').disabled = false;
        
        if (data.status === 'success') {
            // Update the displayed text
            document.getElementById('stegoMessage').value = data.invitation_text;
            alert('Text successfully recreated!');
        } else {
            alert('Text could not be recreated: ' + data.message);
        }
    } catch (error) {
        console.error('Error regenerating text:', error);
        document.getElementById('regeneratingIndicator').classList.remove('show');
        document.getElementById('regenerateBtn').disabled = false;
        alert('An error occured during text recreation.');
    }
}

// Load available models from API when page loads
async function loadAvailableModels() {
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
        console.error('Error loading available models:', error);
    }
}

// Display a styled error message
function displayErrorMessage(message) {
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

// Call loadAvailableModels on page load
document.addEventListener('DOMContentLoaded', loadAvailableModels);

// Theme toggle functionality
document.getElementById('themeToggle').addEventListener('click', function() {
    const currentTheme = document.body.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-bs-theme', newTheme);
    this.querySelector('i').className = newTheme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
});