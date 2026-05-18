# Secure Messenger

A secure REST API for private messaging with end-to-end encryption and real-time message delivery.

## 📋 Overview

Secure Messenger is a two-stage messaging platform that prioritizes user privacy and security:

- **Stage 1**: Core API with user registration, authentication, and encrypted message storage
- **Stage 2**: Real-time message delivery using Server-Sent Events (SSE)

Messages are encrypted on the client side and stored securely on the server. Users authenticate via JWT tokens and passwords are hashed using bcrypt.

## ✨ Features

### Authentication & Security
- User registration and login
- Password hashing with bcrypt (no plaintext storage)
- JWT token-based authentication
- Secure password verification

### Messaging
- Send encrypted messages between users
- Retrieve message history
- Real-time message notifications (Stage 2)
- Message persistence in database

### Real-Time Delivery (Stage 2)
- Server-Sent Events (SSE) for instant message push notifications
- Multiple concurrent connections per user
- Automatic client cleanup on disconnect

## 🛠️ Technology Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: SQLAlchemy with SQLite
- **Authentication**: JWT (python-jose)
- **Cryptography**: Bcrypt, cryptography library
- **Real-Time**: SSE Starlette
- **Testing**: Pytest + pytest-asyncio

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

1. Clone or download the project:
```bash
cd secure-messenger-stage1
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🚀 Running the Application

### Start the Server

```bash
python -m server.main
```

The API will be available at `http://localhost:8000`

**API Documentation**: Visit `http://localhost:8000/docs` for interactive Swagger UI

### Run the Client

In another terminal:
```bash
python client.py
```

### Run Tests

```bash
pytest tests/
```

For Stage 2 tests:
```bash
pytest test_stage2.py -v
```

## 📚 API Endpoints

### Authentication

#### Register
```
POST /register
Content-Type: application/json

{
  "username": "alice",
  "password": "secret123"
}
```

#### Login
```
POST /login
Content-Type: application/json

{
  "username": "alice",
  "password": "secret123"
}

Response:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Messaging

#### Send Message
```
POST /send
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "recipient": "bob",
  "content": "<encrypted_message>"
}
```

#### Get Messages
```
GET /messages/{user}
Authorization: Bearer <TOKEN>
```

### Real-Time (Stage 2)

#### Listen for Messages
```
GET /stream
Authorization: Bearer <TOKEN>

Keeps connection open and pushes messages as they arrive
```

## 📁 Project Structure

```
secure-messenger-stage1/
├── client.py              # Client application
├── requirements.txt       # Python dependencies
├── STAGE_1.md            # Stage 1 documentation
├── STAGE_2.md            # Stage 2 documentation
├── README.md             # This file
├── server/
│   ├── __init__.py
│   ├── main.py           # FastAPI app initialization
│   ├── auth.py           # Authentication logic
│   ├── crypto.py         # Encryption/decryption utilities
│   ├── database.py       # Database setup and queries
│   ├── models.py         # SQLAlchemy models
│   ├── routes.py         # API endpoints
│   └── schemas.py        # Pydantic schemas
└── tests/
    ├── __init__.py
    ├── test_app.py       # Application tests
    └── test_stage2.py    # Real-time messaging tests
```

## 🔐 Security Architecture

### Password Security
- Passwords are hashed with bcrypt before storage
- Original passwords are never stored or logged
- Authentication verifies hashes, not plaintext

### Message Encryption
- Messages are encrypted on the client side
- Server stores encrypted content
- Only intended recipients can decrypt messages

### Token Security
- JWT tokens are signed and time-limited
- Tokens are required for all protected endpoints
- Tokens cannot be forged or modified

## 📖 Usage Example

### Python Client Example

```python
import requests

API_URL = "http://localhost:8000"

# Register
requests.post(f"{API_URL}/register", json={
    "username": "alice",
    "password": "secret123"
})

# Login
response = requests.post(f"{API_URL}/login", json={
    "username": "alice",
    "password": "secret123"
})
token = response.json()["access_token"]

# Send message
requests.post(f"{API_URL}/send", 
    headers={"Authorization": f"Bearer {token}"},
    json={
        "recipient": "bob",
        "content": "encrypted_message_here"
    }
)

# Get messages
response = requests.get(f"{API_URL}/messages/bob",
    headers={"Authorization": f"Bearer {token}"}
)
messages = response.json()
```

## 🧪 Testing

Tests cover:
- User registration and login
- Message sending and retrieval
- Real-time SSE connections
- Authentication and authorization

Run all tests:
```bash
pytest -v
```

## 📝 Development Notes

### Stage 1 (Current)
- REST API with polling-based message retrieval
- Database persistence with SQLAlchemy
- Full authentication and encryption flow

### Stage 2 (Implemented)
- Server-Sent Events for real-time notifications
- Broadcast system for multiple concurrent connections
- Instant message delivery

## 🤝 Contributing

This is an educational project for learning secure messaging patterns.

## 📄 License

Educational use only.

---

For more detailed documentation, see [STAGE_1.md](STAGE_1.md) and [STAGE_2.md](STAGE_2.md)
