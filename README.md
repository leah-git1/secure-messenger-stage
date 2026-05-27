# Secure Messenger — Stage 2

A secure real-time messaging API with end-to-end encryption and Server-Sent Events (SSE).

---

## Project Structure

```
secure-messenger-stage1/
├── client/
│   ├── __init__.py
│   └── client.py          # CLI chat client (SSE listener + message sender)
├── server/
│   ├── __init__.py
│   ├── main.py            # FastAPI app + lifespan
│   ├── routes.py          # All API endpoints
│   ├── broadcaster.py     # SSE fan-out manager (subscribe/publish)
│   ├── auth.py            # bcrypt hashing + JWT tokens
│   ├── crypto.py          # AES-256-GCM encrypt/decrypt
│   ├── database.py        # SQLAlchemy engine + session
│   ├── models.py          # ORM models (User, Message)
│   └── schemas.py         # Pydantic request/response schemas
├── tests/
│   ├── __init__.py
│   └── test_app.py        # Full test suite (Stage 1 + Stage 2 SSE)
├── seed.py                # Populate DB with test users and messages
├── pytest.ini             # Pytest configuration
├── requirements.txt
├── STAGE_1.md
├── STAGE_2.md
└── README.md
```

---

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt
```

---

## Running the Project

### Step 1 — Start the server

```bash
python -m server.main
```

Server runs at `http://localhost:8000`
Interactive API docs: `http://localhost:8000/docs`

### Step 2 — Seed the database (optional, for test data)

```bash
python seed.py
```

Creates users: `alice`, `bob`, `charlie` (password: `password123`) with sample messages.

### Step 3 — Open the CLI client

Open **two terminals** side by side. In each one:

```bash
python -m client.client
```

- Terminal 1: login as `alice`
- Terminal 2: login as `bob`
- Type a message in one terminal → it appears instantly in the other

Example session:
```
=== Secure Messenger ===
1) Register
2) Login
Choose (1/2): 2
Username: alice
Password:

Welcome, alice!  (type your message and press Enter, or 'quit' to exit)
Recipient: bob
  > hey bob, are you there?

  [bob -> alice]: yes! loud and clear
  > great, let's sync at 3pm
```

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output: **22 passed**

```
tests/test_app.py::TestAuthentication::test_register_success         PASSED
tests/test_app.py::TestAuthentication::test_register_duplicate_username PASSED
tests/test_app.py::TestAuthentication::test_register_password_too_short PASSED
tests/test_app.py::TestAuthentication::test_login_success            PASSED
tests/test_app.py::TestAuthentication::test_login_wrong_password     PASSED
tests/test_app.py::TestAuthentication::test_login_unknown_user       PASSED
tests/test_app.py::TestAuthentication::test_messages_require_token   PASSED
tests/test_app.py::TestAuthentication::test_messages_reject_bad_token PASSED
tests/test_app.py::TestAuthentication::test_messages_accept_valid_token PASSED
tests/test_app.py::TestEncryption::test_encrypt_is_not_plain_text    PASSED
tests/test_app.py::TestEncryption::test_decrypt_round_trip           PASSED
tests/test_app.py::TestEncryption::test_same_message_encrypts_differently_each_time PASSED
tests/test_app.py::TestEncryption::test_tampered_ciphertext_raises   PASSED
tests/test_app.py::TestEncryption::test_messages_are_stored_encrypted PASSED
tests/test_app.py::TestMessaging::test_send_message_success          PASSED
tests/test_app.py::TestMessaging::test_get_messages_returns_decrypted PASSED
tests/test_app.py::TestMessaging::test_user_sees_only_their_messages PASSED
tests/test_app.py::TestSSE::test_stream_rejects_no_token             PASSED
tests/test_app.py::TestSSE::test_stream_rejects_bad_token            PASSED
tests/test_app.py::TestSSE::test_sse_stream_receives_broadcast       PASSED
tests/test_app.py::TestSSE::test_only_recipient_sees_targeted_messages PASSED
tests/test_app.py::TestSSE::test_concurrent_clients                  PASSED
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register` | No | Create a new user |
| POST | `/login` | No | Get a JWT token |
| POST | `/messages` | Yes | Send an encrypted message |
| GET | `/messages` | Yes | Fetch your message history (decrypted) |
| GET | `/stream` | Yes | Open SSE connection for real-time delivery |

---

## How It Works

### Stage 1 — Secure REST API
- Passwords hashed with **bcrypt** (one-way, never stored plain)
- Messages encrypted with **AES-256-GCM** before hitting the database
- Authentication via **JWT tokens** (signed, time-limited)
- Users only see messages where they are sender or recipient

### Stage 2 — Real-Time SSE
- `GET /stream` opens a persistent connection per client
- `broadcaster.py` maintains a `SimpleQueue` per connected user
- When `POST /messages` saves a message, it calls `broadcaster.publish()` which puts the message into the recipient's queue
- The SSE generator polls the queue with `get_nowait()` + `asyncio.sleep(0.05)` and streams each message as a `data:` event
- The CLI client runs the SSE listener in a background thread while the main thread handles user input

---

## Security Notes

| What | How |
|------|-----|
| Passwords | bcrypt — one-way hash, never stored plain |
| Messages at rest | AES-256-GCM ciphertext in DB — unreadable without key |
| Authentication | JWT — signed with HS256, expires in 24h |
| Message isolation | Users only receive their own messages via `/stream` |

---

## Technology Stack

- **FastAPI** + **Uvicorn** — async web framework
- **SQLAlchemy** + **SQLite** — ORM and database
- **python-jose** — JWT encoding/decoding
- **bcrypt** — password hashing
- **cryptography** — AES-256-GCM encryption
- **httpx** — HTTP client (CLI + tests)
- **pytest** — test runner
