# Encrypted File Transfer

Encrypted file transfer project for a Computer Security Project.

## Features

- Room creation with a secret key
- Real-time file transfer with WebSocket connection
- Sender/Receiver roles
- Transfer progress information
- Simple and user-friendly interface

## Setup

1. Install Required Packages:
```
pip install -r requirements.txt
```

2. Start App:
```
python main.py
```

3. Go to `http://localhost:8000` in your browser.

## Usage

### Sending
1. Click "Create New Room"
2. Share secret key with receiver
3. Click "Continue As Sender"
4. Wait for receiver information
5. Select file and press "Send File"

### Receiving
1. Click "Join New Room"
2. Enter the secret key received from sender
3. Click "Join"
4. The file will the automatically received after the sender uploads it

## Security

- Cryptographically secure secret key generation
- WebSocket connection validation
- Client-side data integrity validation
