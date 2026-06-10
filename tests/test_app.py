"""
test_app.py — Full test suite (Stage 1 + Stage 2).
"""

import json as _json
import socket
import threading
import time

import httpx as _httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.main import app
from server.models import Base, get_db
from server.crypto import encrypt, decrypt


# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///./test_messenger.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register_and_login(client, username="alice", password="secret123") -> str:
    client.post("/register", json={"username": username, "password": password})
    response = client.post("/login", json={"username": username, "password": password})
    return response.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Authentication tests
# ===========================================================================

class TestAuthentication:

    def test_register_success(self, client):
        response = client.post("/register", json={"username": "alice", "password": "secret123"})
        assert response.status_code == 201

    def test_register_duplicate_username(self, client):
        client.post("/register", json={"username": "alice", "password": "secret123"})
        response = client.post("/register", json={"username": "alice", "password": "other-password"})
        assert response.status_code == 400

    def test_register_password_too_short(self, client):
        response = client.post("/register", json={"username": "alice", "password": "abc"})
        assert response.status_code == 422

    def test_login_success(self, client):
        client.post("/register", json={"username": "alice", "password": "secret123"})
        response = client.post("/login", json={"username": "alice", "password": "secret123"})
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client):
        client.post("/register", json={"username": "alice", "password": "secret123"})
        response = client.post("/login", json={"username": "alice", "password": "wrongpassword"})
        assert response.status_code == 401

    def test_login_unknown_user(self, client):
        response = client.post("/login", json={"username": "ghost", "password": "secret123"})
        assert response.status_code == 401

    def test_messages_require_token(self, client):
        response = client.get("/messages")
        assert response.status_code in (401, 403)

    def test_messages_reject_bad_token(self, client):
        response = client.get("/messages", headers={"Authorization": "Bearer fake-token"})
        assert response.status_code == 401

    def test_messages_accept_valid_token(self, client):
        token = register_and_login(client)
        response = client.get("/messages", headers=auth(token))
        assert response.status_code == 200


# ===========================================================================
# 2. Encryption tests
# ===========================================================================

class TestEncryption:

    def test_encrypt_is_not_plain_text(self):
        assert encrypt("hello world") != "hello world"

    def test_decrypt_round_trip(self):
        original = "this is a secret message"
        assert decrypt(encrypt(original)) == original

    def test_same_message_encrypts_differently_each_time(self):
        assert encrypt("hello") != encrypt("hello")

    def test_tampered_ciphertext_raises(self):
        blob = encrypt("original")
        tampered = blob[:-4] + "XXXX"
        with pytest.raises(Exception):
            decrypt(tampered)

    def test_messages_are_stored_encrypted(self, client):
        from server.models import Message
        token = register_and_login(client, "alice", "password123")
        secret_content = "This is a top secret message"

        client.post(
            "/messages",
            json={"content": secret_content, "recipient": "bob"},
            headers=auth(token),
        )

        db = TestingSession()
        db_message = db.query(Message).filter(Message.sender == "alice").first()
        db.close()

        assert db_message.ciphertext != secret_content
        assert decrypt(db_message.ciphertext) == secret_content


# ===========================================================================
# 3. Messaging tests
# ===========================================================================

class TestMessaging:

    def test_send_message_success(self, client):
        alice_token = register_and_login(client, "alice", "secret123")
        register_and_login(client, "bob", "secret456")

        response = client.post(
            "/messages",
            json={"content": "hello bob", "recipient": "bob"},
            headers=auth(alice_token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "hello bob"
        assert data["sender"] == "alice"
        assert data["recipient"] == "bob"

    def test_get_messages_returns_decrypted(self, client):
        alice_token = register_and_login(client, "alice", "secret123")
        register_and_login(client, "bob", "secret456")

        client.post("/messages", json={"content": "hi bob", "recipient": "bob"}, headers=auth(alice_token))

        response = client.get("/messages", headers=auth(alice_token))
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) >= 1
        assert messages[0]["content"] == "hi bob"

    def test_user_sees_only_their_messages(self, client):
        alice_token   = register_and_login(client, "alice",   "secret123")
        bob_token     = register_and_login(client, "bob",     "secret456")
        charlie_token = register_and_login(client, "charlie", "secret789")

        client.post("/messages", json={"content": "Alice to Bob",   "recipient": "bob"}, headers=auth(alice_token))
        client.post("/messages", json={"content": "Charlie to Bob", "recipient": "bob"}, headers=auth(charlie_token))

        alice_view = client.get("/messages", headers=auth(alice_token)).json()
        assert len(alice_view) == 1
        assert alice_view[0]["content"] == "Alice to Bob"

        bob_view = client.get("/messages", headers=auth(bob_token)).json()
        assert len(bob_view) == 2

        charlie_view = client.get("/messages", headers=auth(charlie_token)).json()
        assert len(charlie_view) == 1
        assert charlie_view[0]["content"] == "Charlie to Bob"


# ===========================================================================
# 4. SSE / Stage 2 tests
# ===========================================================================
# TestClient uses a single anyio event loop — streaming responses and POST
# requests deadlock when sharing it. We spin up a real uvicorn server instead.

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="class")
def live_server():
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(40):
        try:
            _httpx.get(f"http://127.0.0.1:{port}/docs", timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    t.join(timeout=3)


def _reg_login(base: str, username: str, password: str) -> str:
    _httpx.post(f"{base}/register", json={"username": username, "password": password})
    r = _httpx.post(f"{base}/login", json={"username": username, "password": password})
    return r.json()["access_token"]


class TestSSE:

    def test_stream_rejects_no_token(self, client):
        response = client.get("/stream")
        assert response.status_code in (401, 403)

    def test_stream_rejects_bad_token(self, client):
        response = client.get("/stream", headers={"Authorization": "Bearer fake"})
        assert response.status_code == 401

    def test_sse_stream_receives_broadcast(self, live_server):
        """Connect to /stream, send a message, verify it arrives."""
        base = live_server
        alice_token = _reg_login(base, "sse_alice", "secret123")
        bob_token   = _reg_login(base, "sse_bob",   "secret456")

        received = []

        def listen():
            with _httpx.stream("GET", f"{base}/stream",
                               headers={"Authorization": f"Bearer {bob_token}"},
                               timeout=10) as r:
                for line in r.iter_lines():
                    if line.startswith("data: "):
                        received.append(_json.loads(line[6:]))
                        break

        t = threading.Thread(target=listen, daemon=True)
        t.start()
        time.sleep(0.4)

        _httpx.post(f"{base}/messages",
                    json={"content": "hello sse_bob", "recipient": "sse_bob"},
                    headers={"Authorization": f"Bearer {alice_token}"})

        t.join(timeout=5)
        assert len(received) == 1
        assert received[0]["content"] == "hello sse_bob"
        assert received[0]["sender"] == "sse_alice"

    def test_only_recipient_sees_targeted_messages(self, live_server):
        """Alice sends to Bob. Charlie's stream should NOT receive it."""
        base = live_server
        alice_token   = _reg_login(base, "t2_alice",   "secret123")
        bob_token     = _reg_login(base, "t2_bob",     "secret456")
        charlie_token = _reg_login(base, "t2_charlie", "secret789")

        bob_received     = []
        charlie_received = []

        def listen(token, bucket):
            with _httpx.stream("GET", f"{base}/stream",
                               headers={"Authorization": f"Bearer {token}"},
                               timeout=5) as r:
                for line in r.iter_lines():
                    if line.startswith("data: "):
                        bucket.append(_json.loads(line[6:]))
                        break

        tb = threading.Thread(target=listen, args=(bob_token,     bob_received),     daemon=True)
        tc = threading.Thread(target=listen, args=(charlie_token, charlie_received), daemon=True)
        tb.start(); tc.start()
        time.sleep(0.4)

        _httpx.post(f"{base}/messages",
                    json={"content": "secret for t2_bob", "recipient": "t2_bob"},
                    headers={"Authorization": f"Bearer {alice_token}"})

        tb.join(timeout=5)
        tc.join(timeout=2)

        assert len(bob_received) == 1
        assert bob_received[0]["content"] == "secret for t2_bob"
        assert len(charlie_received) == 0

    def test_concurrent_clients(self, live_server):
        """Two clients both connected; both receive messages sent to them."""
        base = live_server
        alice_token = _reg_login(base, "t3_alice", "secret123")
        bob_token   = _reg_login(base, "t3_bob",   "secret456")

        alice_received = []
        bob_received   = []

        def listen(token, bucket, target_content):
            try:
                with _httpx.stream("GET", f"{base}/stream",
                                   headers={"Authorization": f"Bearer {token}"},
                                   timeout=10) as r:
                    for line in r.iter_lines():
                        if line.startswith("data: "):
                            msg = _json.loads(line[6:])
                            bucket.append(msg)
                            if msg["content"] == target_content:
                                break  # got the one we care about
            except (_httpx.ReadTimeout, _httpx.RemoteProtocolError):
                pass

        ta = threading.Thread(target=listen, args=(alice_token, alice_received, "hi t3_alice"), daemon=True)
        tb = threading.Thread(target=listen, args=(bob_token,   bob_received,   "hi t3_bob"),   daemon=True)
        ta.start(); tb.start()
        time.sleep(0.4)

        _httpx.post(f"{base}/messages",
                    json={"content": "hi t3_alice", "recipient": "t3_alice"},
                    headers={"Authorization": f"Bearer {bob_token}"})
        _httpx.post(f"{base}/messages",
                    json={"content": "hi t3_bob", "recipient": "t3_bob"},
                    headers={"Authorization": f"Bearer {alice_token}"})

        ta.join(timeout=6)
        tb.join(timeout=6)

        assert any(m["content"] == "hi t3_alice" for m in alice_received)
        assert any(m["content"] == "hi t3_bob"   for m in bob_received)
