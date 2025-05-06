// encryption.js - Handles encryption and decryption operations
import { addLogEntry } from './ui.js';
import { 
    receivedFileBlob, 
    receivedFileName, 
    encryptionMetadata,
    setReceivedFileBlob
} from './state.js';
import { decryptChaCha } from './api.js';

// Process encrypted file (decryption)
export async function processEncryptedFile() {
    if (!receivedFileBlob || !encryptionMetadata) {
        addLogEntry('File could not be processed: Missing data', 'error');
        return;
    }
    
    try {
        // Read file as ArrayBuffer
        const fileData = await receivedFileBlob.arrayBuffer();
        
        // Determine encryption method used
        const method = encryptionMetadata.method || 'aes-256-gcm';
        
        addLogEntry(`Decrypting file using ${method}...`, 'info');
        
        if (method === 'aes-256-gcm') {
            // Get AES encryption parameters
            const aesKeyHex = encryptionMetadata.aes_key;
            const ivHex = encryptionMetadata.iv;
            const tagHex = encryptionMetadata.tag;
            
            // Validate parameters before proceeding
            if (!aesKeyHex || !ivHex || !tagHex) {
                addLogEntry('Missing AES parameters. Required: aes_key, iv, and tag', 'error');
                
                // Show download button for the encrypted file anyway
                document.getElementById('downloadBtnContainer').style.display = 'block';
                return;
            }
            
            // Convert hex strings to Uint8Array
            const aesKey = hexToUint8Array(aesKeyHex);
            const iv = hexToUint8Array(ivHex);
            const tag = hexToUint8Array(tagHex);
            
            // Decrypt the file using WebCrypto API
            const decryptedData = await decryptFileWithAES(fileData, aesKey, iv, tag);
            
            // Create a blob from decrypted data
            setReceivedFileBlob(new Blob([decryptedData]));
            
            addLogEntry('AES decryption completed successfully', 'success');
        } 
        else if (method === 'chacha20-poly1305') {
            // Get ChaCha20-Poly1305 encryption parameters
            const chachaKeyHex = encryptionMetadata.chacha_key;
            const nonceHex = encryptionMetadata.nonce;
            
            if (!chachaKeyHex || !nonceHex) {
                addLogEntry('Missing ChaCha20-Poly1305 parameters. Required: chacha_key and nonce', 'error');
                
                // Show download button for the encrypted file anyway
                document.getElementById('downloadBtnContainer').style.display = 'block';
                return;
            }
            
            // For ChaCha20-Poly1305, we'll use server-side decryption
            addLogEntry('Preparing ChaCha20-Poly1305 decryption via server...', 'info');
            
            try {
                // Send to server for decryption
                const decryptedBlob = await decryptChaCha(fileData, receivedFileName, chachaKeyHex, nonceHex);
                setReceivedFileBlob(decryptedBlob);
                
                addLogEntry('Server-side ChaCha20 decryption completed', 'success');
            } catch (fetchError) {
                addLogEntry(`Server decryption error: ${fetchError.message}`, 'error');
                throw fetchError;
            }
        }
        
        addLogEntry('Decryption processing finished', 'success');
        
        // Show download button
        document.getElementById('downloadBtnContainer').style.display = 'block';
    } catch (error) {
        addLogEntry('Error with decryption: ' + error.message, 'error');
        console.error('Decryption error details:', error);
        
        // Show download button for the encrypted file
        document.getElementById('downloadBtnContainer').style.display = 'block';
    }
}

// Helper function to convert hex string to Uint8Array
export function hexToUint8Array(hexString) {
    // Check if hexString is undefined or null
    if (!hexString) {
        console.error('hexToUint8Array received undefined or null value');
        return new Uint8Array(0); // Return empty array to prevent errors
    }
    
    const bytes = new Uint8Array(hexString.length / 2);
    for (let i = 0; i < hexString.length; i += 2) {
        bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);
    }
    return bytes;
}

// Decrypt file with AES-GCM using WebCrypto API
export async function decryptFileWithAES(encryptedData, aesKey, iv, tag) {
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
            // Alternate approach - some implementations expect the tag separate from data
            // Try with just the encrypted data without the tag
            return await window.crypto.subtle.decrypt(
                algorithm,
                key,
                encryptedData
            );
        }
    } catch (error) {
        throw new Error("Decryption failed: " + error.message);
    }
}

// Download the received file
export function downloadFile() {
    if (!receivedFileBlob || !receivedFileName) {
        addLogEntry('No file found to download', 'error');
        return;
    }

    // Improved debounce mechanism to prevent duplicate downloads
    if (!window.downloadDebounce) {
        window.downloadDebounce = {
            lastDownloadTime: 0,
            isDownloading: false
        };
    }
    
    const now = Date.now();
    
    // Check if we're already downloading or if it's too soon since the last download
    if (window.downloadDebounce.isDownloading || 
        (now - window.downloadDebounce.lastDownloadTime < 2000)) {
        console.log('Prevented duplicate download');
        return;
    }
    
    // Set downloading state
    window.downloadDebounce.isDownloading = true;
    window.downloadDebounce.lastDownloadTime = now;

    const url = URL.createObjectURL(receivedFileBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = receivedFileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    // Wait a moment before revoking the URL
    setTimeout(() => {
        URL.revokeObjectURL(url);
        // Reset downloading state after a delay
        setTimeout(() => {
            window.downloadDebounce.isDownloading = false;
        }, 500);
    }, 1000);
    
    addLogEntry(`File is downloaded as "${receivedFileName}"`, 'success');
}