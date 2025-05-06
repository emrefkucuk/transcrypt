// state.js - Manages application state
// Global state variables that are shared across modules
export let currentSecretKey = null;
export let currentRole = null; // 'sender' or 'receiver'
export let selectedFile = null;
export let receivedFileData = null;
export let receivedFileName = null;
export let receivedFileBlob = null;
export let receivedChunks = [];
export let totalChunks = 0;
export let encryptionMetadata = null;  // Store encryption metadata for decryption
export let stegoImageFilename = null;  // Store filename for stego image
export let apiFeatures = {  // Available API features
    text_steganography: true,
    image_steganography: true
};

// State setters
export function setCurrentSecretKey(key) {
    currentSecretKey = key;
}

export function setCurrentRole(role) {
    currentRole = role;
}

export function setSelectedFile(file) {
    selectedFile = file;
}

export function setReceivedFileData(data) {
    receivedFileData = data;
}

export function setReceivedFileName(name) {
    receivedFileName = name;
}

export function setReceivedFileBlob(blob) {
    receivedFileBlob = blob;
}

export function addReceivedChunk(chunk) {
    receivedChunks.push(chunk);
}

export function clearReceivedChunks() {
    receivedChunks = [];
}

export function setTotalChunks(count) {
    totalChunks = count;
}

export function setEncryptionMetadata(metadata) {
    encryptionMetadata = metadata;
}

export function setStegoImageFilename(filename) {
    stegoImageFilename = filename;
}

export function setApiFeatures(features) {
    apiFeatures = { ...apiFeatures, ...features };
}

// Reset all state variables
export function resetState() {
    currentSecretKey = null;
    currentRole = null;
    selectedFile = null;
    receivedFileData = null;
    receivedFileName = null;
    receivedFileBlob = null;
    receivedChunks = [];
    totalChunks = 0;
    encryptionMetadata = null;
    stegoImageFilename = null;
}