"""
client/client.py — CLI client for Secure Messenger.

Run with:
    python -m client.client

Interaction example:
    === Secure Messenger ===
    1) Register
    2) Login
    Choose (1/2): 2
    Username: alice
    Password: ••••••••

    Welcome, alice!  (type your message and press Enter, or 'quit' to exit)
    Recipient: bob
    > hello bob!
    [bob -> alice]: hey, got your message!
    >
"""

import getpass
import json
import sys
import threading

import httpx

BASE_URL = "http://localhost:8000"


def prompt_auth(client: httpx.Client) -> tuple[str, str]:
    """Handle register/login. Returns (username, token)."""
    print("\n=== Secure Messenger ===")
    while True:
        print("1) Register\n2) Login")
        choice = input("Choose (1/2): ").strip()
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")

        if choice == "1":
            r = client.post(f"{BASE_URL}/register", json={"username": username, "password": password})
            if r.status_code == 201:
                print("Registered! Now logging in...")
            else:
                print(f"Error: {r.json().get('detail', r.text)}")
                continue

        r = client.post(f"{BASE_URL}/login", json={"username": username, "password": password})
        if r.status_code == 200:
            token = r.json()["access_token"]
            print(f"\nWelcome, {username}!  (type your message and press Enter, or 'quit' to exit)")
            return username, token
        print(f"Login failed: {r.json().get('detail', r.text)}")


def listen_for_messages(token: str) -> None:
    """Background thread: open /stream and print incoming messages."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with httpx.stream("GET", f"{BASE_URL}/stream", headers=headers, timeout=None) as r:
            for line in r.iter_lines():
                if line.startswith("data: "):
                    try:
                        msg = json.loads(line[6:])
                        print(f"\n  [{msg['sender']} -> {msg['recipient']}]: {msg['content']}")
                        print("  > ", end="", flush=True)
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass  # server closed or client exited


def main() -> None:
    with httpx.Client(timeout=10.0) as client:
        username, token = prompt_auth(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Show message history
        r = client.get(f"{BASE_URL}/messages", headers=headers)
        if r.status_code == 200:
            msgs = r.json()
            if msgs:
                print("\n--- History ---")
                for m in msgs:
                    print(f"  [{m['sender']} -> {m['recipient']}]: {m['content']}")
                print("--- End ---\n")

        # Start SSE listener in background
        t = threading.Thread(target=listen_for_messages, args=(token,), daemon=True)
        t.start()

        recipient = input("Recipient: ").strip()

        while True:
            try:
                text = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                sys.exit(0)

            if text.lower() == "quit":
                print("Goodbye!")
                sys.exit(0)
            if not text:
                continue

            r = client.post(
                f"{BASE_URL}/messages",
                json={"content": text, "recipient": recipient},
                headers=headers,
            )
            if r.status_code != 201:
                print(f"  Send failed: {r.json().get('detail', r.text)}")


if __name__ == "__main__":
    main()
