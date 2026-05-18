# Stage 2: Real-Time Messaging with Server-Sent Events (SSE)

## 🎯 Overview

Stage 1 was a **polling REST API**—clients asked the server for messages repeatedly.

Stage 2 adds **real-time push notifications** via **Server-Sent Events (SSE)**. Instead of polling, clients open a persistent connection that receives messages instantly as soon as they arrive.

### The Problem Stage 2 Solves

```
STAGE 1 (Polling):
  Bob: "Any new messages?" → Server: "No"
  Bob: "Any new messages?" → Server: "No"
  Bob: "Any new messages?" → Server: "No"
  Alice sends message...
  Bob: "Any new messages?" → Server: "Yes! Here's Alice's message"
  
  ❌ Wasteful, slow, and requires Bob to keep asking

STAGE 2 (Push):
  Bob: "I'm listening..." (connection stays open)
  Alice sends message...
  Server: "✨ Message from Alice!" (pushed to Bob's open connection)
  
  ✅ Instant, efficient, no polling needed
```

---

## 🔧 What Was Implemented

### 1. **Broadcast System** (`server/routes.py`)

Added a global registry of connected SSE clients:

```python
_active_clients: dict[str, set[Queue]] = {}
```

- When a user connects to `/stream`, they get added to this registry
- When a message is sent to a user, all their open connections receive it
- Automatically cleans up disconnected clients

### 2. **SSE Endpoint** (`GET /stream`)

```
GET /stream
Authorization: Bearer <JWT_TOKEN>
```

Opens a persistent HTTP connection that:
- Listens for incoming messages in an infinite loop
- Pushes messages as Server-Sent Events (format: `data: {...}\n\n`)
- Stays open until the client disconnects

**Example connection:**
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/stream
```

Output:
```
data: {"id": 3, "sender": "alice", "recipient": "bob", "content": "Hello!", "created_at": "2026-05-18T..."}
```

### 3. **Message Broadcasting** (`send_message` route)

When Alice sends a message to Bob, the server now:
1. Saves the encrypted message to the database (as before)
2. **Broadcasts it instantly** to Bob's SSE stream(s)

```python
await _broadcast_message(body.recipient, message_event)
```

### 4. **CLI Client** (`client.py`)

A terminal-based client that demonstrates real-time chat:

```
✓ Logged in as 'alice'
Commands:
  send    - Send a message
  history - View message history
  quit    - Exit

alice: send
Send to (username): bob
Message: Hello Bob! 👋
✓ Message sent to bob

[📨 NEW MESSAGE] bob: Hi Alice! 👋
```

The client:
- Maintains an open SSE connection in the background
- Allows the user to type and send messages
- Displays incoming messages in real-time
- Uses asyncio to handle simultaneous listening and typing

---

## 📋 Files Added/Modified

### Added Files:
- **`client.py`** — CLI client with real-time message streaming
- **`test_stage2.py`** — Test script demonstrating SSE functionality

### Modified Files:
- **`server/routes.py`**
  - Added `_active_clients` registry
  - Added `_broadcast_message()` function
  - Added `GET /stream` endpoint
  - Modified `send_message()` to broadcast messages

---

## 🚀 How to Use Stage 2

### 1. Start the Server
```bash
python -m uvicorn server.main:app --reload
```

Server runs on `http://localhost:8000`

### 2. Run the CLI Client
```bash
python client.py
```

Follow the prompts to register or login. Then:
- Type `send` to send a message
- Type `history` to view messages
- Type `quit` to exit

### 3. Multiple Clients
Open multiple terminal windows and run `python client.py` multiple times:

```
Terminal 1: alice connecting...   │ Terminal 2: bob connecting...
alice: [listening]                │ bob: [listening]
                                  │
[Message arrives for alice]       │
[📨 NEW MESSAGE] bob: Hello!      │
alice: send                        │
Send to: bob                       │
Message: Hi Bob!                  │
✓ Sent                            │ [📨 NEW MESSAGE] alice: Hi Bob!
```

### 4. Run the Test
```bash
python test_stage2.py
```

---

## ✅ Test Results

The test script (`test_stage2.py`) verifies:

1. **User Registration** — Multiple users can register
2. **Authentication** — Users receive JWT tokens
3. **SSE Streaming** — Open connection to `/stream` succeeds
4. **Real-time Delivery** — Message sent by Alice is instantly received by Bob through SSE
5. **Message History** — GET `/messages` still works for historical retrieval

**Output:**
```
✅ SUCCESS! Bob received message through SSE stream!
Message: {'id': 3, 'sender': 'alice', 'recipient': 'bob', 'content': 'Hello Bob! 🎉', 'created_at': '2026-05-18T...'}
```

---

## 🔐 Security Notes

- **Authentication:** SSE endpoint requires valid JWT token (same as POST `/messages`)
- **Encryption:** Messages are still encrypted end-to-end
- **Privacy:** Users only receive messages where they are the recipient
- **Connection Safety:** Disconnected clients are automatically cleaned up

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                   CLIENT 1 (Alice)          │
│  ┌──────────────────────────────────────┐  │
│  │ Send Messages                        │  │
│  │ POST /messages                       │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ Listen via SSE                       │  │
│  │ GET /stream (persistent)             │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
          ↓                         ↑
          POST /messages            SSE push
               ↓                     ↑
┌─────────────────────────────────────────────┐
│              SERVER (FastAPI)               │
│  ┌──────────────────────────────────────┐  │
│  │ Database (SQLite)                    │  │
│  │ - Users, Messages                    │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ Broadcast Registry                   │  │
│  │ _active_clients = {                  │  │
│  │   "bob": {queue1, queue2},           │  │
│  │   "alice": {queue3}                  │  │
│  │ }                                    │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
          ↑                         ↓
          SSE push                 POST /messages
               ↑                     ↓
┌─────────────────────────────────────────────┐
│                   CLIENT 2 (Bob)            │
│  ┌──────────────────────────────────────┐  │
│  │ Send Messages                        │  │
│  │ POST /messages                       │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ Listen via SSE                       │  │
│  │ GET /stream (persistent)             │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## 📚 Key Concepts

### Server-Sent Events (SSE)
- HTTP protocol for one-directional server → client streaming
- Like a radio: you tune in once and listen for broadcasts
- Format: `data: JSON\n\n` (two newlines required)
- Much simpler than WebSockets for one-way push

### Asyncio Tasks
- Background task listens on the SSE stream
- Main task handles user input
- Both run simultaneously in the CLI client

### Queue-Based Broadcasting
- Each connected client has an asyncio Queue
- When a message arrives, it's put into recipient's queues
- Each client pops from their queue and yields as SSE

---

## 🔮 What's Next? (Stage 3)

Possible enhancements:
- **Group chats** — broadcast to multiple recipients
- **Message reactions** — 👍 on messages
- **Typing indicators** — "Alice is typing..."
- **Read receipts** — "Bob read your message"
- **WebSocket upgrade** — for bidirectional communication
- **Persistence** — store chat history permanently
- **Database optimization** — indexes for faster queries
- **Load balancing** — multiple server instances with Redis pub/sub

---

## 📖 References

- [FastAPI SSE Documentation](https://fastapi.tiangolo.com/advanced/sse/)
- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [SSE-Starlette Library](https://github.com/sysid/sse-starlette)
- [Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

---

**Status:** ✅ Stage 2 Complete and Tested
