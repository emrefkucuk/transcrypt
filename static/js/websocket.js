// websocket.js - Handles WebSocket communication
import { showNotification, addLogEntry, displayErrorMessage } from './ui.js';
import { 
    currentRole, 
    currentSecretKey, 
    setReceivedFileBlob,
    setEncryptionMetadata,
    setReceivedFileName,
    receivedFileName,
    receivedFileBlob,
    encryptionMetadata,
    selectedFile
} from './state.js';
import { processEncryptedFile } from './encryption.js';
import { initP2PConnection, processAnswer, addIceCandidate, sendP2PData, closeP2PConnection } from './p2p.js';

// Global WebSocket instance
let wsConnection = null;
// Add a flag to track ongoing transfers
let transferInProgress = false;
// Make WebSocket accessible to other modules
window.wsConnection = null;

// Store file metadata for P2P transfers
let pendingP2PFileMetadata = null;

// Create a P2P message handler and expose it globally for the P2P module to use
window.handleP2PMessage = function(data) {
    try {
        // Check if this is a binary transfer (ArrayBuffer)
        if (data instanceof ArrayBuffer) {
            // This could be either a whole file or a chunk of a file
            if (pendingP2PFileMetadata && pendingP2PFileMetadata.chunkedTransfer) {
                // Handle file chunk
                const chunkData = data;
                
                // Add the chunk to our collection
                pendingP2PFileMetadata.chunks = pendingP2PFileMetadata.chunks || [];
                pendingP2PFileMetadata.chunks.push(chunkData);
                
                // Update progress based on received chunks
                const progress = Math.min(Math.round((pendingP2PFileMetadata.chunks.length / pendingP2PFileMetadata.totalChunks) * 95) + 5, 100);
                document.getElementById('progressBar').style.width = `${progress}%`;
                document.getElementById('progressBar').textContent = `${progress}%`;
                
                // Check if we have all chunks
                if (pendingP2PFileMetadata.chunks.length === pendingP2PFileMetadata.totalChunks) {
                    // All chunks received, combine them
                    addLogEntry(`All ${pendingP2PFileMetadata.totalChunks} chunks received, assembling file...`, 'info');
                    
                    // Calculate total size
                    let totalSize = 0;
                    pendingP2PFileMetadata.chunks.forEach(chunk => {
                        totalSize += chunk.byteLength;
                    });
                    
                    // Create a new array to hold the complete file
                    const completeFile = new Uint8Array(totalSize);
                    
                    // Copy each chunk into the correct position
                    let offset = 0;
                    pendingP2PFileMetadata.chunks.forEach(chunk => {
                        completeFile.set(new Uint8Array(chunk), offset);
                        offset += chunk.byteLength;
                    });
                    
                    // Create a blob from the complete file
                    const blob = new Blob([completeFile], { type: 'application/octet-stream' });
                    setReceivedFileBlob(blob);
                    
                    // Use the metadata we stored earlier
                    setReceivedFileName(pendingP2PFileMetadata.name);
                    
                    // If encryption is needed, store the encryption metadata
                    if (pendingP2PFileMetadata.encryptionOptions && 
                        pendingP2PFileMetadata.encryptionOptions.method !== 'none') {
                        setEncryptionMetadata({
                            method: pendingP2PFileMetadata.encryptionOptions.method,
                            // Add any encryption-specific metadata here
                        });
                    }
                    
                    // Show download button
                    document.getElementById('downloadBtnContainer').style.display = 'block';
                    
                    // Indicate transfer completion
                    addLogEntry('File transfer via P2P complete!', 'success');
                    showNotification('File received successfully!', 'success');
                    
                    // Update progress to 100%
                    document.getElementById('progressBar').style.width = '100%';
                    document.getElementById('progressBar').textContent = '100%';
                    
                    // Clear the pending metadata
                    pendingP2PFileMetadata = null;
                }
                
                return;
            } else if (pendingP2PFileMetadata) {
                // Legacy mode - single binary transfer
                addLogEntry('Received binary file data via P2P', 'info');
                
                // Update progress to 100%
                document.getElementById('progressBar').style.width = '100%';
                document.getElementById('progressBar').textContent = '100%';
                
                // Create a Blob from the binary data
                const blob = new Blob([data], { type: 'application/octet-stream' });
                setReceivedFileBlob(blob);
                
                // Use the metadata we stored earlier
                setReceivedFileName(pendingP2PFileMetadata.name);
                
                // If encryption is needed, store the encryption metadata
                if (pendingP2PFileMetadata.encryptionOptions && 
                    pendingP2PFileMetadata.encryptionOptions.method !== 'none') {
                    setEncryptionMetadata({
                        method: pendingP2PFileMetadata.encryptionOptions.method,
                        // Add any encryption-specific metadata here
                    });
                }
                
                // Show download button
                document.getElementById('downloadBtnContainer').style.display = 'block';
                
                // Indicate transfer completion
                addLogEntry('File transfer via P2P complete!', 'success');
                showNotification('File received successfully!', 'success');
                
                // Clear the pending metadata
                pendingP2PFileMetadata = null;
                return;
            } else {
                addLogEntry('Received binary data but no metadata found', 'error');
                return;
            }
        }
        
        // If not binary, parse the JSON message
        const message = JSON.parse(data);
        
        // Handle file metadata message
        if (message.type === 'file_metadata') {
            // Store the metadata for when we receive the binary data
            pendingP2PFileMetadata = message;
            pendingP2PFileMetadata.chunkedTransfer = true; // Flag for chunked transfer
            pendingP2PFileMetadata.chunks = []; // Initialize chunks array
            
            // Log received file metadata
            addLogEntry(`Receiving file via P2P: ${message.name} (${formatFileSize(message.size)})`, 'info');
            
            // Show the file information on the UI
            document.getElementById('transferProgress').style.display = 'block';
            document.getElementById('progressBar').style.width = '5%';
            document.getElementById('progressBar').textContent = '5%';
            document.getElementById('fileInfo').textContent = `Receiving file: ${message.name}`;
            
            // Hide the waiting message
            const waitingAlert = document.querySelector('#receiverInterface .alert-info');
            if (waitingAlert) {
                waitingAlert.style.display = 'none';
            }
            
            // Show encryption information if available
            if (message.encryptionOptions) {
                document.getElementById('encryptionInfo').style.display = 'block';
                
                let methodText = 'Encryption: ';
                if (message.encryptionOptions.method === 'aes-256-gcm') {
                    methodText += 'AES-256-GCM';
                    addLogEntry('File is encrypted with AES-256-GCM', 'info');
                } else if (message.encryptionOptions.method === 'chacha20-poly1305') {
                    methodText += 'ChaCha20-Poly1305';
                    addLogEntry('File is encrypted with ChaCha20-Poly1305', 'info');
                } else {
                    methodText += 'No Encryption';
                    addLogEntry('File sending without encryption', 'info');
                }
                document.getElementById('encryptionMethodInfo').textContent = methodText;
                
                let integrityText = 'Integrity Validation: ';
                if (message.encryptionOptions.integrityCheck) {
                    integrityText += 'Active (SHA-256)';
                    addLogEntry('SHA-256 integrity validation active', 'info');
                } else {
                    integrityText += 'Passive';
                    addLogEntry('Integrity validation inactive', 'warning');
                }
                document.getElementById('integrityCheckInfo').textContent = integrityText;
            }
            
            addLogEntry('Waiting for file data...', 'info');
            return;
        }
        
        // Handle chunk metadata message
        if (message.type === 'file_chunk') {
            if (!pendingP2PFileMetadata || !pendingP2PFileMetadata.chunkedTransfer) {
                addLogEntry('Received chunk metadata but no file transfer is in progress', 'error');
                return;
            }
            
            // Store total chunks from first chunk message
            if (message.chunk_index === 0) {
                pendingP2PFileMetadata.totalChunks = message.total_chunks;
                addLogEntry(`File will be received in ${message.total_chunks} chunks`, 'info');
            }
            
            // Record the expected chunk index for the next binary message
            pendingP2PFileMetadata.nextChunkIndex = message.chunk_index;
            
            return;
        }
        
        // Handle legacy format (single message with data embedded)
        if (message.type === 'file') {
            // This is the old format - should be updated, but we'll support it for backward compatibility
            addLogEntry('Received file via P2P (legacy format)', 'warning');
            
            // Log received file
            addLogEntry(`Received file via P2P: ${message.name} (${formatFileSize(message.size)})`, 'success');
            
            // Show the file information on the UI
            document.getElementById('transferProgress').style.display = 'block';
            document.getElementById('progressBar').style.width = '100%';
            document.getElementById('progressBar').textContent = '100%';
            document.getElementById('fileInfo').textContent = `Receiving file: ${message.name}`;
            
            // Hide the waiting message
            const waitingAlert = document.querySelector('#receiverInterface .alert-info');
            if (waitingAlert) {
                waitingAlert.style.display = 'none';
            }
            
            // Show encryption information if available
            if (message.encryptionOptions) {
                document.getElementById('encryptionInfo').style.display = 'block';
                
                let methodText = 'Encryption: ';
                if (message.encryptionOptions.method === 'aes-256-gcm') {
                    methodText += 'AES-256-GCM';
                    addLogEntry('File is encrypted with AES-256-GCM', 'info');
                } else if (message.encryptionOptions.method === 'chacha20-poly1305') {
                    methodText += 'ChaCha20-Poly1305';
                    addLogEntry('File is encrypted with ChaCha20-Poly1305', 'info');
                } else {
                    methodText += 'No Encryption';
                    addLogEntry('File sending without encryption', 'info');
                }
                document.getElementById('encryptionMethodInfo').textContent = methodText;
                
                let integrityText = 'Integrity Validation: ';
                if (message.encryptionOptions.integrityCheck) {
                    integrityText += 'Active (SHA-256)';
                    addLogEntry('SHA-256 integrity validation active', 'info');
                } else {
                    integrityText += 'Passive';
                    addLogEntry('Integrity validation inactive', 'warning');
                }
                document.getElementById('integrityCheckInfo').textContent = integrityText;
            }
            
            try {
                // In legacy format, we have to handle data differently
                const fileData = message.data;
                // Note: This legacy format is likely not working well with binary data
                const blob = new Blob([fileData], { type: 'application/octet-stream' });
                setReceivedFileBlob(blob);
                setReceivedFileName(message.name);
                
                if (message.encryptionOptions && message.encryptionOptions.method !== 'none') {
                    setEncryptionMetadata({
                        method: message.encryptionOptions.method,
                        // Other encryption metadata would be added here in a real implementation
                    });
                }
                
                addLogEntry('File data processed successfully', 'success');
            } catch (error) {
                addLogEntry(`Error processing file data: ${error.message}`, 'error');
                console.error('Error processing file data:', error);
                return;
            }
            
            // Show download button
            document.getElementById('downloadBtnContainer').style.display = 'block';
            
            // Indicate transfer completion
            addLogEntry('File transfer via P2P complete!', 'success');
            showNotification('File received successfully!', 'success');
        }
        
        // Handle other message types here if needed
        
    } catch (error) {
        // If we get here with binary data, it means we failed to process it
        if (typeof data !== 'string') {
            addLogEntry(`Error processing binary file data: ${error.message}`, 'error');
            console.error('Error processing binary file data:', error);
        } else {
            addLogEntry(`Error processing P2P message: ${error.message}`, 'error');
            console.error('Error processing P2P message:', error);
        }
    }
};

// Connect to WebSocket
export function connectWebSocket(role) {
    if (wsConnection) {
        wsConnection.close();
    }
    
    // Reset transfer flag when connecting
    transferInProgress = false;
    
    const connectionStatus = document.getElementById('connectionStatus');
    connectionStatus.textContent = 'Connecting...';
    
    // Create WebSocket connection
    wsConnection = new WebSocket(`ws://${window.location.host}/ws/${role}/${currentSecretKey}`);
    window.wsConnection = wsConnection;
    window.signalChannel = wsConnection;
    
    wsConnection.onopen = () => {
        connectionStatus.textContent = 'Connected';
        addLogEntry('Connected to server', 'info');
        
        if (role === 'sender') {
            checkFileInputState();
        }
        
        // Initialize P2P connection if enabled - check if element exists first
        const p2pElement = document.getElementById('usePeerToPeer');
        if (p2pElement && p2pElement.checked) {
            initP2PConnection(role, wsConnection);
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
            addLogEntry(`Connection closed with code ${event.code}: ${event.reason || 'Unknown reason'}`, 'error');
            
            // If it's a maximum receiver error, show specific notification
            if (event.reason.includes('Maximum number of receivers')) {
                showNotification('Room has reached maximum capacity', 'danger');
            }
        }
    };
    
    wsConnection.onerror = (error) => {
        connectionStatus.textContent = 'Error';
        addLogEntry('WebSocket connection error', 'error');
        console.error('WebSocket error:', error);
    };
    
    wsConnection.onmessage = handleWebSocketMessage;
}

// Close active WebSocket connection
export function closeWebSocket() {
    if (wsConnection) {
        wsConnection.close();
        wsConnection = null;
        window.wsConnection = null;
    }
    
    // Also close P2P connection
    closeP2PConnection();
}

// Handle WebSocket messages
function handleWebSocketMessage(event) {
    try {
        if (typeof event.data === 'string') {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'room_status':
                    updateRoomStatus(data);
                    break;
                case 'status':
                    // For backward compatibility
                    updateRoomStatus(data);
                    break;
                case 'connected':
                    // When connected message is received, log it
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
                case 'p2p-signal':
                    // WebRTC signaling message
                    if (data.signal.type === 'answer') {
                        processAnswer(data.signal);
                    } else if (data.signal.candidate) {
                        addIceCandidate(data.signal);
                    }
                    break;
                default:
                    console.log('Unhandled message type:', data.type, data);
                    break;
            }
        } else if (currentRole === 'receiver') {
            // Binary data - we now get a complete file at once, not chunks
            // Use the setter function instead of directly assigning to the constant
            setReceivedFileBlob(new Blob([event.data]));
            addLogEntry('File received, processing...', 'info');
        }
    } catch (error) {
        console.error('Error processing WebSocket message:', error, event.data);
        addLogEntry('Error processing WebSocket message', 'error');
    }
}

// Update room status based on WebSocket message
function updateRoomStatus(data) {
    // Update sender and receiver counts in UI
    if (data.senders !== undefined) {
        document.getElementById('senderCount').textContent = data.senders;
    }
    if (data.receivers !== undefined) {
        document.getElementById('receiverCount').textContent = data.receivers;
    }
    
    // Enable/disable send button based on conditions
    if (currentRole === 'sender') {
        checkFileInputState();
        
        const receiverCount = parseInt(document.getElementById('receiverCount').textContent);
        
        if (receiverCount > 0) {
            addLogEntry('Receiver connected, you may send a file', 'info');
        } else {
            addLogEntry('Waiting for receiver connection', 'info');
        }
    }
}

// Send file through WebSocket or P2P
export function sendFile() {
    // First check if file is selected
    if (!selectedFile) {
        showNotification('No file selected', 'danger');
        return;
    }

    // Check if we're in P2P mode
    const p2pStatusElement = document.getElementById('p2pStatus');
    const isPeerToPeer = p2pStatusElement && (p2pStatusElement.textContent === 'Connected' || 
                                             p2pStatusElement.textContent.includes('Connected'));
    
    if (isPeerToPeer) {
        // Try to send via P2P
        addLogEntry('Attempting to send file via P2P connection...', 'info');
        
        // Show progress UI
        document.getElementById('transferProgress').style.display = 'block';
        document.getElementById('progressBar').style.width = '0%';
        document.getElementById('progressBar').textContent = '0%';
        
        // Get encryption options
        const encryptionOptions = {
            method: document.getElementById('encryptionMethod').value,
            integrityCheck: document.getElementById('integrityCheck').checked
        };
        
        // Disable the send button during transfer
        document.getElementById('sendFileBtn').disabled = true;
        
        // Display file info
        document.getElementById('fileInfo').textContent = 
            `Sending file: ${selectedFile.name} (${formatFileSize(selectedFile.size)})`;
        
        // Log encryption options
        if (encryptionOptions.method === 'aes-256-gcm') {
            addLogEntry('File will be encrypted with AES-256-GCM', 'info');
        } else if (encryptionOptions.method === 'chacha20-poly1305') {
            addLogEntry('File will be encrypted with ChaCha20-Poly1305', 'info');
        } else {
            addLogEntry('File will be sent without encryption', 'warning');
        }
        
        if (encryptionOptions.integrityCheck) {
            addLogEntry('SHA-256 integrity validation active', 'info');
        }

        // Read the file as ArrayBuffer before sending
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                // Send file metadata first
                const metadataStr = JSON.stringify({
                    type: 'file_metadata',
                    name: selectedFile.name,
                    size: selectedFile.size,
                    encryptionOptions: encryptionOptions
                });
                
                // Update progress UI to show metadata sent
                document.getElementById('progressBar').style.width = '5%';
                document.getElementById('progressBar').textContent = '5%';
                
                // Send the metadata
                if (!sendP2PData(metadataStr)) {
                    throw new Error('Failed to send file metadata');
                }
                
                // Use a smaller chunk size for P2P transfers
                const chunkSize = 16 * 1024; // 16KB chunks
                const fileData = e.target.result;
                const totalChunks = Math.ceil(fileData.byteLength / chunkSize);
                
                addLogEntry(`Preparing to send file in ${totalChunks} chunks...`, 'info');
                
                // Create a function to send chunks sequentially
                let currentChunk = 0;
                
                const sendNextChunk = () => {
                    if (currentChunk >= totalChunks) {
                        // All chunks sent
                        document.getElementById('progressBar').style.width = '100%';
                        document.getElementById('progressBar').textContent = '100%';
                        
                        addLogEntry('File transfer via P2P completed', 'success');
                        showNotification('File sent successfully', 'success');
                        
                        // Re-enable send button
                        setTimeout(() => {
                            document.getElementById('sendFileBtn').disabled = false;
                        }, 1000);
                        
                        return;
                    }
                    
                    // Calculate chunk boundaries
                    const start = currentChunk * chunkSize;
                    const end = Math.min(start + chunkSize, fileData.byteLength);
                    
                    // Create chunk data with metadata
                    const chunkMetadata = {
                        type: 'file_chunk',
                        chunk_index: currentChunk,
                        total_chunks: totalChunks
                    };
                    
                    // Send chunk metadata
                    if (!sendP2PData(JSON.stringify(chunkMetadata))) {
                        addLogEntry(`Error sending chunk ${currentChunk + 1} metadata`, 'error');
                        setTimeout(sendNextChunk, 500); // Retry after a delay
                        return;
                    }
                    
                    // Extract the chunk data
                    const chunk = fileData.slice(start, end);
                    
                    // Send the chunk data
                    if (!sendP2PData(chunk)) {
                        addLogEntry(`Error sending chunk ${currentChunk + 1}`, 'error');
                        setTimeout(sendNextChunk, 500); // Retry after a delay
                        return;
                    }
                    
                    // Update progress
                    const progress = Math.min(Math.round(((currentChunk + 1) / totalChunks) * 95) + 5, 100);
                    document.getElementById('progressBar').style.width = `${progress}%`;
                    document.getElementById('progressBar').textContent = `${progress}%`;
                    
                    // Increment chunk counter
                    currentChunk++;
                    
                    // Schedule the next chunk to be sent with a small delay
                    setTimeout(sendNextChunk, 100);
                };
                
                // Start sending chunks after a short delay to allow metadata processing
                setTimeout(sendNextChunk, 500);
                
            } catch (error) {
                addLogEntry(`Error sending file: ${error.message}`, 'error');
                showNotification('Error sending file', 'danger');
                document.getElementById('sendFileBtn').disabled = false;
            }
        };
        
        reader.onerror = function() {
            addLogEntry('Error reading file', 'error');
            showNotification('Error reading file', 'danger');
            document.getElementById('sendFileBtn').disabled = false;
        };
        
        // Start reading file as ArrayBuffer
        addLogEntry('Reading file data...', 'info');
        reader.readAsArrayBuffer(selectedFile);
        return;
    }
    
    // If not P2P, use WebSocket
    if (!wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
        showNotification('WebSocket connection not established', 'danger');
        return;
    }

    // Prevent duplicate transfers
    if (transferInProgress) {
        showNotification('Transfer already in progress', 'warning');
        return;
    }

    // Set transfer in progress flag
    transferInProgress = true;

    // Get encryption options
    const encryptionOptions = {
        method: document.getElementById('encryptionMethod').value,
        integrityCheck: document.getElementById('integrityCheck').checked
    };

    // Show progress UI
    document.getElementById('transferProgress').style.display = 'block';
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressBar').textContent = '0%';
    
    addLogEntry('Starting file transfer via WebSocket...', 'info');
    
    // Log encryption options
    if (encryptionOptions.method === 'aes-256-gcm') {
        addLogEntry('File will be encrypted with AES-256-GCM', 'info');
    } else if (encryptionOptions.method === 'chacha20-poly1305') {
        addLogEntry('File will be encrypted with ChaCha20-Poly1305', 'info');
    } else {
        addLogEntry('File will be sent without encryption', 'warning');
    }
    
    if (encryptionOptions.integrityCheck) {
        addLogEntry('SHA-256 integrity validation active', 'info');
    }

    // Disable the send button during transfer to prevent multiple sends
    document.getElementById('sendFileBtn').disabled = true;

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

// Handle the start of a file transfer
function handleTransferStart(data) {
    document.getElementById('transferProgress').style.display = 'block';
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressBar').textContent = '0%';
    
    if (currentRole === 'receiver') {
        // Reset variables using setter functions
        setReceivedFileBlob(null);
        setEncryptionMetadata(null);
        setReceivedFileName(data.filename);
        
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
            } else if (data.encryptionOptions.method === 'chacha20-poly1305') {
                methodText += 'ChaCha20-Poly1305';
                addLogEntry('File is encrypted with ChaCha20-Poly1305', 'info');
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
        // Use setter function instead of directly modifying the constant
        setEncryptionMetadata(data.encryption_metadata);
        
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
    // Reset transfer flag when complete
    transferInProgress = false;
    
    // Re-enable the send button if appropriate
    if (currentRole === 'sender') {
        checkFileInputState();
    }

    addLogEntry('File transfer successful', 'success');
    
    if (currentRole === 'receiver') {
        setReceivedFileName(data.filename);
        
        // Process the received file if it's encrypted
        if (encryptionMetadata && encryptionMetadata.method) {
            // Check which encryption method is used
            if (encryptionMetadata.method === 'aes-256-gcm' && encryptionMetadata.aes_key) {
                // For AES-256-GCM
                addLogEntry('Decrypting AES-256-GCM encrypted file', 'info');
                processEncryptedFile();
            } 
            else if (encryptionMetadata.method === 'chacha20-poly1305' && encryptionMetadata.chacha_key) {
                // For ChaCha20-Poly1305
                addLogEntry('Decrypting ChaCha20-Poly1305 encrypted file', 'info');
                processEncryptedFile();
            }
            else {
                // If method is specified but keys missing, show warning
                addLogEntry('Encryption method specified but decryption keys missing', 'warning');
                document.getElementById('downloadBtnContainer').style.display = 'block';
            }
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

// Handle error messages from the server
function handleErrorMessage(data) {
    // Reset transfer flag on error
    transferInProgress = false;
    
    // Re-enable the send button if appropriate
    if (currentRole === 'sender') {
        checkFileInputState();
    }

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
                window.wsConnection = null;
            }
            
            // If we're in receiver mode, go back to join options
            if (currentRole === 'receiver') {
                document.getElementById('fileTransfer').style.display = 'none';
                document.getElementById('joinRoomOptions').style.display = 'block';
            }
        }, 1000);
    }
}

// Check if send button should be enabled
export function checkFileInputState() {
    const sendBtn = document.getElementById('sendFileBtn');
    if (!sendBtn) return;
    
    // Get the file input element
    const fileInput = document.getElementById('fileInput');
    if (!fileInput) return;
    
    // Check if a file is selected
    const hasFile = fileInput.files && fileInput.files.length > 0;
    
    // Get the P2P status element to check if in P2P mode
    const p2pStatusElement = document.getElementById('p2pStatus');
    const isPeerToPeer = p2pStatusElement && 
                        (p2pStatusElement.textContent === 'Connected' || 
                         p2pStatusElement.textContent.includes('Connected'));
    
    if (isPeerToPeer) {
        // In P2P mode, delegate to the P2P module's checkFileInputState function
        import('./p2p.js').then(({ checkFileInputState: p2pCheckFileInputState, isP2PConnected }) => {
            if (isP2PConnected()) {
                const hasFile = fileInput.files && fileInput.files.length > 0;
                sendBtn.disabled = !(isP2PConnected() && hasFile);
            } else {
                sendBtn.disabled = true;
            }
        }).catch(error => {
            // Fallback if module import fails
            sendBtn.disabled = !hasFile;
        });
    } else {
        // In WebSocket mode
        if (hasFile && wsConnection && wsConnection.readyState === WebSocket.OPEN && !transferInProgress) {
            sendBtn.disabled = false;
        } else {
            sendBtn.disabled = true;
        }
    }
}

// Format file size for display
export function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' bytes';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    else return (bytes / 1073741824).toFixed(1) + ' GB';
}