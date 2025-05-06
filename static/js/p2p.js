// p2p.js - Handles peer-to-peer connections
import { addLogEntry, showNotification, showConnectionCodeContainer, showConnectionCodeInput, generateConnectionCode, updateP2PStatusDisplay, updateP2PParticipantCounts } from './ui.js';
import { currentRole, setCurrentRole } from './state.js';

// Global variables
let peerConnection = null;
let dataChannel = null;
let pendingCandidates = [];
let connectionCode = null;
let lastReceivedCode = null;

// Setup localStorage event listening for cross-tab communication
window.addEventListener('storage', handleStorageEvent);

// Initialize WebRTC peer connection
export function initP2PConnection(role, websocket) {
    // Close any existing connection first
    closeP2PConnection();
    
    // Create RTCPeerConnection with configuration optimized for local network
    peerConnection = new RTCPeerConnection({
        iceServers: [
            // Add minimal STUN servers - these help with NAT traversal but aren't always needed on local networks
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ],
        // Enable ICE TCP to improve local network connections
        iceTransportPolicy: 'all',
        // Prioritize local network connections
        iceCandidatePoolSize: 0
    });
    
    // Set up event handlers
    setupPeerConnectionEvents();
    
    // If we're the sender, create the data channel
    if (role === 'sender') {
        // Create a data channel with options optimized for file transfer
        dataChannel = peerConnection.createDataChannel('fileTransfer', {
            ordered: true,           // Guarantee packet order
            maxRetransmits: 30,      // Retry up to 30 times for reliability
            priority: 'high'         // High priority for data
        });
        setupDataChannel();
        
        // Create offer
        createOffer();
        
        // Add event listener to file input to update send button state
        setupFileInputListener();
    } else {
        // Receiver listens for data channel
        peerConnection.ondatachannel = (event) => {
            dataChannel = event.channel;
            setupDataChannel();
        };
    }
}

// Add event listener to file input element to update send button state when a file is selected
function setupFileInputListener() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            checkFileInputState();
        });
    }
}

// Initialize P2P with connection code-based signaling
export function initP2PWithCode(role, websocket) {
    // Save role in state
    setCurrentRole(role);
    
    // Initialize the peer connection
    initP2PConnection(role, websocket);
    
    if (role === 'sender') {
        // Generate and show connection code for sender
        connectionCode = generateConnectionCode();
        showConnectionCodeContainer();
        
        // Set up our signal server data in localStorage
        const signalData = {
            offer: null,
            candidates: [],
            answer: null,
            receiverCandidates: [],
            timestamp: Date.now()
        };
        localStorage.setItem(`p2p_signal_${connectionCode}`, JSON.stringify(signalData));
        
        // Log the connection code for debugging
        addLogEntry(`Connection code generated: ${connectionCode}`, 'info');
        addLogEntry('Share this code with the receiver to establish connection', 'info');
    } else {
        // Show connection code input field for receiver
        showConnectionCodeInput();
        addLogEntry('Enter the connection code provided by the sender', 'info');
    }
}

// Handle localStorage changes from other tabs or windows
function handleStorageEvent(event) {
    if (!event.key || !event.newValue) return;
    
    // If it's our P2P signal data
    if (event.key.startsWith('p2p_signal_')) {
        const code = event.key.replace('p2p_signal_', '');
        const signalData = JSON.parse(event.newValue);
        
        // Process signal data updates based on our role
        processSignalDataUpdate(code, signalData);
    }
}

// Process updates to signal data in localStorage
function processSignalDataUpdate(code, signalData) {
    // If we're the receiver and just provided this code
    if (currentRole === 'receiver' && lastReceivedCode === code) {
        // Check if there's an offer available now
        if (signalData.offer && !peerConnection.remoteDescription) {
            processReceivedOffer(signalData.offer, signalData.candidates || []);
        }
    }
    
    // If we're the sender and this is our code
    if (currentRole === 'sender' && connectionCode === code) {
        // Check if there's an answer now
        if (signalData.answer && !peerConnection.remoteDescription) {
            processAnswer(signalData.answer);
            
            // Add any receiver candidates
            if (signalData.receiverCandidates && signalData.receiverCandidates.length > 0) {
                signalData.receiverCandidates.forEach(candidate => {
                    addIceCandidate(candidate);
                });
            }
        } else if (signalData.receiverCandidates && signalData.receiverCandidates.length > 0) {
            // Just process new ICE candidates
            const lastKnownSignalData = getSignalData(code);
            const knownCandidatesCount = lastKnownSignalData.receiverCandidates ? 
                lastKnownSignalData.receiverCandidates.length : 0;
            
            if (signalData.receiverCandidates.length > knownCandidatesCount) {
                for (let i = knownCandidatesCount; i < signalData.receiverCandidates.length; i++) {
                    addIceCandidate(signalData.receiverCandidates[i]);
                }
            }
        }
    }
}

// Actively poll for updates to signal data (for devices on same network)
function startSignalPolling(code) {
    // Store the polling interval ID so we can clear it later
    if (window.signalPollingInterval) {
        clearInterval(window.signalPollingInterval);
    }
    
    // Start polling every 500ms
    window.signalPollingInterval = setInterval(() => {
        const signalData = getSignalData(code);
        processSignalDataUpdate(code, signalData);
    }, 500);
    
    // Stop polling after 60 seconds (connection should be established by then)
    setTimeout(() => {
        if (window.signalPollingInterval) {
            clearInterval(window.signalPollingInterval);
            window.signalPollingInterval = null;
        }
    }, 60000);
}

// Set up event listeners for peer connection
function setupPeerConnectionEvents() {
    // ICE candidate event
    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            // Log candidate type (useful for debugging local vs. remote candidates)
            const candidateType = event.candidate.candidate.split(' ')[7]; // Extract type from SDP
            addLogEntry(`Generated ICE candidate (${candidateType})`, 'info');
            
            // Store the candidate for later use with the connection code
            pendingCandidates.push(event.candidate);
            
            // Update the signal data in localStorage based on role
            if (currentRole === 'sender' && connectionCode) {
                const signalData = getSignalData(connectionCode);
                signalData.candidates.push(event.candidate);
                updateSignalData(connectionCode, signalData);
            } else if (currentRole === 'receiver' && lastReceivedCode) {
                const signalData = getSignalData(lastReceivedCode);
                signalData.receiverCandidates.push(event.candidate);
                updateSignalData(lastReceivedCode, signalData);
            }
        } else {
            // This indicates that all ICE candidates have been gathered
            addLogEntry('All ICE candidates gathered', 'info');
        }
    };
    
    // ICE gathering state change
    peerConnection.onicegatheringstatechange = () => {
        addLogEntry(`ICE gathering state: ${peerConnection.iceGatheringState}`, 'info');
    };
    
    // Connection state change
    peerConnection.onconnectionstatechange = () => {
        addLogEntry(`P2P connection state: ${peerConnection.connectionState}`, 'info');
        
        // Update status display based on connection state
        if (peerConnection.connectionState === 'connected') {
            updateP2PStatusDisplay(true);
            updateP2PParticipantCounts(); // Update participant counts
            showNotification('Peer-to-peer connection established', 'success');
            
            // Stop polling once connected
            if (window.signalPollingInterval) {
                clearInterval(window.signalPollingInterval);
                window.signalPollingInterval = null;
            }
        } else if (peerConnection.connectionState === 'disconnected' || 
                  peerConnection.connectionState === 'failed' ||
                  peerConnection.connectionState === 'closed') {
            updateP2PStatusDisplay(false);
            updateP2PParticipantCounts(); // Update participant counts
        }
    };
    
    // ICE connection state change
    peerConnection.oniceconnectionstatechange = () => {
        addLogEntry(`ICE connection state: ${peerConnection.iceConnectionState}`, 'info');
        
        // Also use ICE connection state for UI updates
        if (peerConnection.iceConnectionState === 'connected' || peerConnection.iceConnectionState === 'completed') {
            updateP2PStatusDisplay(true);
        }
    };
    
    // Signaling state change
    peerConnection.onsignalingstatechange = () => {
        addLogEntry(`Signaling state: ${peerConnection.signalingState}`, 'info');
    };
}

// Set up data channel event handlers
function setupDataChannel() {
    dataChannel.onopen = () => {
        addLogEntry('Data channel opened', 'success');
        updateP2PStatusDisplay(true);
        
        // Update participant counts
        updateP2PParticipantCounts();
        
        // Enable the send button when connected as sender
        if (currentRole === 'sender') {
            checkFileInputState();
        }
    };
    
    dataChannel.onclose = () => {
        addLogEntry('Data channel closed', 'info');
        updateP2PStatusDisplay(false);
        
        // Disable send button when connection is closed
        if (currentRole === 'sender') {
            const sendBtn = document.getElementById('sendFileBtn');
            if (sendBtn) sendBtn.disabled = true;
        }
    };
    
    dataChannel.onerror = (error) => {
        // Handle error correctly with proper error information
        // The RTCDataChannel error event might not have a message property
        const errorMessage = error.message || error.error || 'Unknown data channel error';
        addLogEntry(`Data channel error: ${errorMessage}`, 'error');
        
        // Don't close the channel on error - let it auto-recover if possible
        console.error('Data channel error event:', error);
    };
    
    // Handle incoming data
    dataChannel.onmessage = (event) => {
        // Forward the message to the appropriate handler in websocket.js
        if (window.handleP2PMessage) {
            window.handleP2PMessage(event.data);
        } else {
            addLogEntry('Received P2P message but no handler is available', 'warning');
        }
    };
}

// Send file data over P2P connection
export function sendP2PData(data) {
    if (!dataChannel || dataChannel.readyState !== 'open') {
        addLogEntry('Data channel not open, can\'t send data', 'error');
        return false;
    }
    
    try {
        // Send the data through the channel
        // Note: dataChannel.send() can handle both strings and binary data (ArrayBuffer)
        
        // For large data (especially files), try to use buffered sending
        // to avoid overwhelming the data channel
        if (data instanceof ArrayBuffer && data.byteLength > 16384) {
            // For large files, check buffer amount and wait if needed
            if (dataChannel.bufferedAmount > 16777216) { // 16MB buffer limit
                addLogEntry('Data channel buffer full, waiting before sending more data', 'warning');
                
                // Return false to indicate send failure, caller should retry
                return false;
            }
        }
        
        // Send the data
        dataChannel.send(data);
        
        // For large binary transfers (files), log the size
        if (data instanceof ArrayBuffer) {
            const dataSize = data.byteLength / (1024 * 1024);
            addLogEntry(`Sent binary data: ${dataSize.toFixed(2)} MB`, 'info');
        }
        
        return true;
    } catch (error) {
        addLogEntry(`Error sending data: ${error.message}`, 'error');
        return false;
    }
}

// Create and send offer
async function createOffer() {
    try {
        // Create offer with options optimized for file transfer
        const offerOptions = {
            offerToReceiveAudio: false,
            offerToReceiveVideo: false,
            iceRestart: false
        };
        
        const offer = await peerConnection.createOffer(offerOptions);
        await peerConnection.setLocalDescription(offer);
        addLogEntry('Created connection offer', 'info');
        
        // Store the offer in our signal server data
        if (connectionCode) {
            const signalData = getSignalData(connectionCode);
            signalData.offer = offer;
            updateSignalData(connectionCode, signalData);
        }
    } catch (error) {
        addLogEntry(`Error creating offer: ${error.message}`, 'error');
    }
}

// Process an offer from a sender (called by the receiver)
async function processReceivedOffer(offer, candidates = []) {
    try {
        const rtcSessionDescription = new RTCSessionDescription(offer);
        await peerConnection.setRemoteDescription(rtcSessionDescription);
        addLogEntry('Processed offer from sender', 'info');
        
        // Add ICE candidates from the sender
        for (const candidate of candidates) {
            await addIceCandidate(candidate);
        }
        
        // Create an answer
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        addLogEntry('Created answer in response to offer', 'info');
        
        // Store the answer in the signal data
        if (lastReceivedCode) {
            const signalData = getSignalData(lastReceivedCode);
            signalData.answer = answer;
            updateSignalData(lastReceivedCode, signalData);
        }
    } catch (error) {
        addLogEntry(`Error processing offer: ${error.message}`, 'error');
        showNotification('Error connecting to peer', 'danger');
    }
}

// Process answer from remote peer
export async function processAnswer(answer) {
    if (!peerConnection) return;
    
    try {
        const rtcSessionDescription = new RTCSessionDescription(answer);
        await peerConnection.setRemoteDescription(rtcSessionDescription);
        addLogEntry('Processed answer from receiver', 'info');
    } catch (error) {
        addLogEntry(`Error processing answer: ${error.message}`, 'error');
    }
}

// Add ICE candidate from remote peer
export async function addIceCandidate(candidate) {
    if (!peerConnection) return;
    
    try {
        await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
        const candidateType = candidate.candidate ? candidate.candidate.split(' ')[7] : 'unknown';
        addLogEntry(`Added ICE candidate (${candidateType})`, 'info');
    } catch (error) {
        addLogEntry(`Error adding ICE candidate: ${error.message}`, 'error');
    }
}

// Close peer connection
export function closeP2PConnection() {
    // Stop signal polling if it's running
    if (window.signalPollingInterval) {
        clearInterval(window.signalPollingInterval);
        window.signalPollingInterval = null;
    }
    
    if (dataChannel) {
        dataChannel.close();
        dataChannel = null;
    }
    
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    
    pendingCandidates = [];
    
    // If we're the sender, clean up the signal server data
    if (currentRole === 'sender' && connectionCode) {
        localStorage.removeItem(`p2p_signal_${connectionCode}`);
        connectionCode = null;
    }
    
    // If we're the receiver, clean up the last received code
    if (currentRole === 'receiver') {
        lastReceivedCode = null;
    }
    
    // Update UI to show disconnected state
    updateP2PStatusDisplay(false);
}

// Helper functions for working with the stored signal data
function getSignalData(code) {
    try {
        const stored = localStorage.getItem(`p2p_signal_${code}`);
        return stored ? JSON.parse(stored) : {
            offer: null,
            candidates: [],
            answer: null,
            receiverCandidates: [],
            timestamp: Date.now()
        };
    } catch (e) {
        console.error('Error parsing signal data', e);
        return {
            offer: null,
            candidates: [],
            answer: null,
            receiverCandidates: [],
            timestamp: Date.now()
        };
    }
}

function updateSignalData(code, data) {
    data.timestamp = Date.now();
    localStorage.setItem(`p2p_signal_${code}`, JSON.stringify(data));
}

// Validate and process connection code
export async function validateConnectionCode(inputCode) {
    try {
        if (!inputCode || inputCode.trim() === '') {
            showNotification('Please enter a connection code', 'warning');
            return;
        }
        
        const formattedCode = inputCode.trim().toUpperCase();
        
        // Save the received code
        lastReceivedCode = formattedCode;
        
        // Check if the code exists in our signal data store
        const signalData = getSignalData(formattedCode);
        
        if (!signalData.offer) {
            // If there's no offer yet, start polling for it
            addLogEntry('Waiting for sender connection information...', 'info');
            showNotification('Waiting for sender connection information...', 'info');
            startSignalPolling(formattedCode);
            return;
        }
        
        // Process the offer and create an answer
        await processReceivedOffer(signalData.offer, signalData.candidates || []);
        
        // Start polling for updates (to catch any future ICE candidates)
        startSignalPolling(formattedCode);
        
        addLogEntry('Connection code validated and offer processed', 'success');
        showNotification('Connection request sent', 'success');
    } catch (error) {
        addLogEntry(`Connection code validation error: ${error.message}`, 'error');
        showNotification('Failed to process connection code', 'danger');
    }
}

// Check if P2P is connected and ready
export function isP2PConnected() {
    return peerConnection && 
           (peerConnection.connectionState === 'connected' || peerConnection.iceConnectionState === 'connected') && 
           dataChannel && 
           dataChannel.readyState === 'open';
}

// Check if the send button should be enabled for P2P transfers
export function checkFileInputState() {
    const sendBtn = document.getElementById('sendFileBtn');
    const fileInput = document.getElementById('fileInput');
    
    if (!sendBtn || !fileInput) {
        return; // Exit if elements don't exist
    }
    
    const isConnected = isP2PConnected();
    const hasFile = fileInput.files && fileInput.files.length > 0;
    
    // Enable button if connected and file selected
    if (isConnected && hasFile) {
        sendBtn.disabled = false;
    } else {
        sendBtn.disabled = true;
    }
}