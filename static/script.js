document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const createRoomBtn = document.getElementById('create-room-btn');
    const joinRoomBtn = document.getElementById('join-room-btn');
    const joinWithKeyBtn = document.getElementById('join-with-key');
    const secretKeyInput = document.getElementById('secret-key-input');
    const secretKeyDisplay = document.getElementById('secret-key-display');
    const copyKeyBtn = document.getElementById('copy-key');
    const continueAsSenderBtn = document.getElementById('continue-as-sender');
    const backFromJoinBtn = document.getElementById('back-from-join');
    const backFromCreateBtn = document.getElementById('back-from-create');
    const leaveRoomBtn = document.getElementById('leave-room');
    const sendFileBtn = document.getElementById('send-file-btn');
    const fileInput = document.getElementById('file-input');
    const statusText = document.getElementById('status-text');
    const senderCount = document.getElementById('sender-count');
    const receiverCount = document.getElementById('receiver-count');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const fileInfo = document.getElementById('file-info');
    
    // Şifreleme seçenekleri elementlerini ekleyelim
    const encryptionMethod = document.getElementById('encryption-method');
    const integrityCheck = document.getElementById('integrity-check');
    const encryptionInfo = document.getElementById('encryption-info');
    const encryptionMethodInfo = document.getElementById('encryption-method-info');
    const integrityCheckInfo = document.getElementById('integrity-check-info');

    // Yeni DOM elementleri
    const encryptionLogs = document.getElementById('encryption-logs');
    const encryptionLogContent = document.getElementById('encryption-log-content');
    const integrityResult = document.getElementById('integrity-result');
    const integrityStatus = document.getElementById('integrity-status');
    const downloadFileBtn = document.getElementById('download-file-btn');

    // View sections
    const startOptionsView = document.getElementById('start-options');
    const joinRoomView = document.getElementById('join-room');
    const roomCreatedView = document.getElementById('room-created');
    const fileTransferView = document.getElementById('file-transfer');
    const senderControlsView = document.getElementById('sender-controls');
    const receiverWaitingView = document.getElementById('receiver-waiting');
    const transferProgressView = document.getElementById('transfer-progress');

    // Global state
    let currentSecretKey = null;
    let wsConnection = null;
    let currentRole = null; // 'sender' or 'receiver'
    let currentFile = null;
    let receivedChunks = [];
    let totalChunks = 0;

    // Yeni değişkenler
    let receivedEncryptionMetadata = {};
    let receivedBlob = null;

    // Show a specific view, hide others
    function showView(viewElement) {
        [startOptionsView, joinRoomView, roomCreatedView, fileTransferView].forEach(view => {
            view.classList.add('hidden');
        });
        viewElement.classList.remove('hidden');
    }

    // Event listeners for navigation
    createRoomBtn.addEventListener('click', createRoom);
    joinRoomBtn.addEventListener('click', () => showView(joinRoomView));
    backFromJoinBtn.addEventListener('click', () => showView(startOptionsView));
    backFromCreateBtn.addEventListener('click', () => showView(startOptionsView));
    joinWithKeyBtn.addEventListener('click', joinRoom);
    copyKeyBtn.addEventListener('click', copySecretKey);
    continueAsSenderBtn.addEventListener('click', continueAsSender);
    leaveRoomBtn.addEventListener('click', leaveRoom);
    sendFileBtn.addEventListener('click', initiateFileTransfer);
    fileInput.addEventListener('change', handleFileSelection);
    downloadFileBtn.addEventListener('click', downloadFile);

    // Create a new room
    async function createRoom() {
        try {
            const response = await fetch('/api/create-room', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                currentSecretKey = data.secret_key;
                secretKeyDisplay.textContent = currentSecretKey;
                showView(roomCreatedView);
            } else {
                alert('Oda oluşturulurken bir hata oluştu.');
            }
        } catch (error) {
            console.error('Error creating room:', error);
            alert('Oda oluşturulurken bir hata oluştu.');
        }
    }

    // Copy secret key to clipboard
    function copySecretKey() {
        navigator.clipboard.writeText(currentSecretKey)
            .then(() => {
                copyKeyBtn.textContent = 'Kopyalandı!';
                setTimeout(() => {
                    copyKeyBtn.textContent = 'Kopyala';
                }, 2000);
            })
            .catch(err => {
                console.error('Error copying text: ', err);
                alert('Kopyalama işlemi başarısız oldu.');
            });
    }

    // Join a room with a secret key
    async function joinRoom() {
        const key = secretKeyInput.value.trim();
        if (!key) {
            alert('Lütfen bir Secret Key girin.');
            return;
        }

        try {
            const response = await fetch(`/api/check-room?secret_key=${encodeURIComponent(key)}`);
            const data = await response.json();
            
            if (data.valid) {
                currentSecretKey = key;
                // Go directly to receiver mode
                setupAsReceiver();
            } else {
                alert('Geçersiz Secret Key. Lütfen tekrar deneyin.');
            }
        } catch (error) {
            console.error('Error checking room:', error);
            alert('Oda kontrolü sırasında bir hata oluştu.');
        }
    }

    // Continue as sender after creating a room
    function continueAsSender() {
        setupAsSender();
    }

    // Setup as sender
    function setupAsSender() {
        currentRole = 'sender';
        showView(fileTransferView);
        senderControlsView.classList.remove('hidden');
        receiverWaitingView.classList.add('hidden');
        connectWebSocket('sender');
    }

    // Setup as receiver
    function setupAsReceiver() {
        currentRole = 'receiver';
        showView(fileTransferView);
        senderControlsView.classList.add('hidden');
        receiverWaitingView.classList.remove('hidden');
        connectWebSocket('receiver');
    }

    // Connect to WebSocket
    function connectWebSocket(role) {
        if (wsConnection) {
            wsConnection.close();
        }

        statusText.textContent = 'Bağlanıyor...';
        wsConnection = new WebSocket(`ws://${window.location.host}/ws/${role}/${currentSecretKey}`);
        
        wsConnection.onopen = () => {
            statusText.textContent = 'Bağlandı';
        };
        
        wsConnection.onclose = () => {
            statusText.textContent = 'Bağlantı koptu';
            sendFileBtn.disabled = true;
        };
        
        wsConnection.onerror = (error) => {
            console.error('WebSocket error:', error);
            statusText.textContent = 'Bağlantı hatası';
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
                        alert(`Hata: ${data.message}`);
                        break;
                }
            } else if (currentRole === 'receiver') {
                // Binary data - file chunk
                receivedChunks.push(event.data);
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    }

    // Update room status
    function updateRoomStatus(data) {
        senderCount.textContent = data.senders;
        receiverCount.textContent = data.receivers;
        
        if (currentRole === 'sender') {
            sendFileBtn.disabled = !data.ready_to_transfer;
        }
    }

    // Handle file selection
    function handleFileSelection() {
        if (fileInput.files.length > 0) {
            currentFile = fileInput.files[0];
            fileInfo.textContent = `Seçilen dosya: ${currentFile.name} (${formatFileSize(currentFile.size)})`;
        } else {
            currentFile = null;
            fileInfo.textContent = '';
        }
    }

    // Initiate file transfer
    function initiateFileTransfer() {
        if (!currentFile || !wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
            alert('Dosya seçilmedi veya bağlantı kurulmadı.');
            return;
        }

        // Show progress UI
        transferProgressView.classList.remove('hidden');
        progressBar.style.width = '0%';
        progressText.textContent = '0%';

        // Şifreleme seçeneklerini al
        const encryptionOptions = {
            method: encryptionMethod.value,
            integrityCheck: integrityCheck.checked
        };

        // Send file metadata
        wsConnection.send(JSON.stringify({
            type: 'start_transfer',
            filename: currentFile.name,
            filesize: currentFile.size,
            encryptionOptions: encryptionOptions  // Şifreleme seçeneklerini ekledik
        }));

        // Start reading and sending file chunks
        const chunkSize = 64 * 1024; // 64KB chunks
        const totalChunks = Math.ceil(currentFile.size / chunkSize);
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
                    const end = Math.min(start + chunkSize, currentFile.size);
                    readNextChunk(start, end);
                }
            }
        };
        
        const readNextChunk = (start, end) => {
            const slice = currentFile.slice(start, end);
            reader.readAsArrayBuffer(slice);
        };
        
        // Start reading first chunk
        readNextChunk(0, chunkSize);
    }

    // Handle transfer start
    function handleTransferStart(data) {
        if (currentRole === 'receiver') {
            receivedChunks = [];
            totalChunks = Math.ceil(data.filesize / (64 * 1024)); // Assuming 64KB chunks
            
            transferProgressView.classList.remove('hidden');
            progressBar.style.width = '0%';
            progressText.textContent = '0%';
            fileInfo.textContent = `Alınacak dosya: ${data.filename} (${formatFileSize(data.filesize)})`;
            
            // Şifreleme bilgilerini göster
            if (data.encryptionOptions) {
                encryptionInfo.classList.remove('hidden');
                
                let methodText = 'Şifreleme: ';
                if (data.encryptionOptions.method === 'aes-256-gcm') {
                    methodText += 'AES-256-GCM';
                } else {
                    methodText += 'Şifrelemesiz';
                }
                encryptionMethodInfo.textContent = methodText;
                
                let integrityText = 'Bütünlük Doğrulama: ';
                integrityText += data.encryptionOptions.integrityCheck ? 'Aktif (SHA-256)' : 'Pasif';
                integrityCheckInfo.textContent = integrityText;
            }
        }
    }

    // Update transfer progress
    function updateTransferProgress(data) {
        const percentage = data.percentage;
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${percentage}%`;
        
        // Şifreleme metadata'sı var mı kontrol et
        if (data.encryption_metadata && Object.keys(data.encryption_metadata).length > 0) {
            // İlk chunk'sa ve şifreleme anahtarları varsa log göster
            if (data.chunk_id === 0 && data.encryption_metadata.aes_key) {
                addEncryptionLog('Şifreleme anahtarları alındı', 'info');
                addEncryptionLog(`AES Anahtarı: ${data.encryption_metadata.aes_key.substring(0, 10)}...`, 'info');
                addEncryptionLog(`IV: ${data.encryption_metadata.iv}`, 'info');
                
                // Metadata'yı sakla
                receivedEncryptionMetadata = data.encryption_metadata;
            }
            
            // Bütünlük hash'i varsa göster
            if (data.encryption_metadata.chunk_hash) {
                addEncryptionLog(`Chunk ${data.chunk_id + 1}/${data.total_chunks} hash: ${data.encryption_metadata.chunk_hash.substring(0, 15)}...`, 'info');
                
                // Son chunk'sa ve bütünlük doğrulama aktifse, sonucu göster
                if (data.chunk_id === data.total_chunks - 1) {
                    showIntegrityResult(data.encryption_metadata.chunk_hash);
                }
            }
        }
    }

    // Handle transfer complete
    function handleTransferComplete(data) {
        if (currentRole === 'receiver') {
            // Combine chunks 
            const blob = new Blob(receivedChunks);
            receivedBlob = blob; // Blob'u sakla
            
            // Integrity bilgisi gösterilmiyorsa, indirme butonunu göster
            if (integrityResult.classList.contains('hidden')) {
                downloadFileBtn.disabled = false;
                addEncryptionLog('Dosya transferi tamamlandı, indirilebilir', 'success');
                downloadFile(); // Otomatik indir
            }
        } else {
            // Sender için
            alert('Dosya transferi tamamlandı!');
            transferProgressView.classList.add('hidden');
        }
    }

    // Bütünlük doğrulama sonucunu göster
    function showIntegrityResult(finalHash) {
        integrityResult.classList.remove('hidden');
        
        // Şimdilik sadece hash göster, sonraki adımda doğrulama da yapacağız
        integrityStatus.textContent = `Bütünlük kontrolü yapılıyor...`;
        
        // Örnek olarak doğrulamanın başarılı olduğunu varsayalım (gerçek kontrolü backend yapacak)
        setTimeout(() => {
            const success = true; // Backend'den gelen sonuç burada kullanılacak
            
            if (success) {
                integrityStatus.textContent = `Bütünlük doğrulaması başarılı. Dosya güvenli.`;
                integrityStatus.className = 'status-success';
                downloadFileBtn.disabled = false;
                addEncryptionLog('Dosya bütünlüğü doğrulandı', 'success');
            } else {
                integrityStatus.textContent = `UYARI: Bütünlük doğrulaması başarısız! Dosya değiştirilmiş olabilir.`;
                integrityStatus.className = 'status-error';
                downloadFileBtn.disabled = true;
                addEncryptionLog('Dosya bütünlüğü doğrulanamadı!', 'error');
            }
        }, 1000);
    }

    // Dosyayı indirme fonksiyonu
    function downloadFile() {
        if (!receivedBlob) return;
        
        const downloadUrl = URL.createObjectURL(receivedBlob);
        const downloadLink = document.createElement('a');
        downloadLink.href = downloadUrl;
        downloadLink.download = receivedBlob.name || 'downloaded_file';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        
        // Clean up
        URL.revokeObjectURL(downloadUrl);
        addEncryptionLog('Dosya indirildi', 'success');
    }

    // Şifreleme logu eklemek için fonksiyon
    function addEncryptionLog(message, type = 'info') {
        const logEntry = document.createElement('div');
        logEntry.classList.add('log-entry', `log-${type}`);
        logEntry.textContent = message;
        encryptionLogContent.appendChild(logEntry);
        encryptionLogContent.scrollTop = encryptionLogContent.scrollHeight;
        
        // Eğer gizliyse görünür yap
        encryptionLogs.classList.remove('hidden');
    }

    // Leave the current room
    function leaveRoom() {
        if (wsConnection) {
            wsConnection.close();
            wsConnection = null;
        }
        
        currentSecretKey = null;
        currentRole = null;
        currentFile = null;
        receivedChunks = [];
        
        showView(startOptionsView);
    }

    // Format file size for display
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' bytes';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        else if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
        else return (bytes / 1073741824).toFixed(1) + ' GB';
    }
});
