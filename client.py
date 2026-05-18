#!/usr/bin/env python3
"""
client.py — CLI Client for Secure Messenger Stage 2

This is a terminal-based client that:
  1. Connects to the server and authenticates
  2. Sends messages via POST /messages
  3. Listens to incoming messages via SSE stream (GET /stream)
  4. Displays messages in real-time as they arrive

USAGE:
  python client.py

Then follow the prompts to register or login, and start chatting!
"""

import httpx
import asyncio
import json
import sys
import getpass
from typing import Optional


BASE_URL = "http://localhost:8000"
TOKEN: Optional[str] = None
USERNAME: Optional[str] = None


async def register(client: httpx.AsyncClient) -> None:
    """Register a new user."""
    print("\n--- Register ---")
    username = input("Username (3-50 chars): ").strip()
    password = getpass.getpass("Password (6+ chars): ")
    
    try:
        response = await client.post(
            f"{BASE_URL}/register",
            json={"username": username, "password": password},
        )
        response.raise_for_status()
        print(f"✓ User '{username}' registered successfully!")
    except httpx.HTTPStatusError as e:
        print(f"✗ Registration failed: {e.response.json()['detail']}")


async def login(client: httpx.AsyncClient) -> bool:
    """Login and get JWT token."""
    global TOKEN, USERNAME
    
    print("\n--- Login ---")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    
    try:
        response = await client.post(
            f"{BASE_URL}/login",
            json={"username": username, "password": password},
        )
        response.raise_for_status()
        data = response.json()
        TOKEN = data["access_token"]
        USERNAME = username
        print(f"✓ Logged in as '{username}'")
        return True
    except httpx.HTTPStatusError as e:
        print(f"✗ Login failed: {e.response.json()['detail']}")
        return False


async def listen_for_messages(client: httpx.AsyncClient) -> None:
    """
    Open the /stream endpoint and listen for incoming messages.
    This runs in a background task while the user types.
    """
    if not TOKEN:
        print("✗ Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        print(f"\n[Listening for messages on stream...]\n")
        async with client.stream(
            "GET",
            f"{BASE_URL}/stream",
            headers=headers,
            timeout=None,  # Keep connection open indefinitely
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        message_json = line[6:]  # Remove "data: " prefix
                        msg = json.loads(message_json)
                        print(
                            f"\n[📨 NEW MESSAGE] {msg['sender']}: {msg['content']}"
                            f"\n"
                        )
                        print("You: ", end="", flush=True)
                    except json.JSONDecodeError:
                        pass
    except asyncio.CancelledError:
        print("\n[Stream disconnected]")
    except Exception as e:
        print(f"\n✗ Stream error: {e}")


async def send_message(client: httpx.AsyncClient) -> None:
    """Send a message to another user."""
    global TOKEN
    
    if not TOKEN:
        print("✗ Not authenticated")
        return
    
    recipient = input("Send to (username): ").strip()
    content = input("Message: ").strip()
    
    if not content:
        return
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        response = await client.post(
            f"{BASE_URL}/messages",
            json={"content": content, "recipient": recipient},
            headers=headers,
        )
        response.raise_for_status()
        msg = response.json()
        print(f"✓ Message sent to {recipient}")
    except httpx.HTTPStatusError as e:
        try:
            error = e.response.json()
            print(f"✗ Failed to send: {error['detail']}")
        except:
            print(f"✗ Failed to send message (HTTP {e.response.status_code})")


async def fetch_messages(client: httpx.AsyncClient) -> None:
    """Fetch all historical messages."""
    global TOKEN
    
    if not TOKEN:
        print("✗ Not authenticated")
        return
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    try:
        response = await client.get(
            f"{BASE_URL}/messages",
            headers=headers,
        )
        response.raise_for_status()
        messages = response.json()
        
        if not messages:
            print("\n(No messages yet)")
        else:
            print(f"\n--- Message History ({len(messages)} total) ---")
            for msg in messages:
                print(
                    f"{msg['created_at'][:19]} | {msg['sender']} → {msg['recipient']}: {msg['content']}"
                )
    except httpx.HTTPStatusError as e:
        print(f"✗ Failed to fetch messages: {e}")


async def stream_task(client: httpx.AsyncClient) -> None:
    """Background task to listen to the stream."""
    try:
        await listen_for_messages(client)
    except Exception as e:
        print(f"Stream task error: {e}")


async def main() -> None:
    """Main client loop."""
    global TOKEN, USERNAME
    
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     Secure Messenger Stage 2 - CLI Client                ║")
    print("║     Real-time chat with Server-Sent Events (SSE)         ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Auth loop
        while not TOKEN:
            print("\n1. Register")
            print("2. Login")
            choice = input("Choose (1/2): ").strip()
            
            if choice == "1":
                await register(client)
            elif choice == "2":
                success = await login(client)
                if success:
                    break
            else:
                print("Invalid choice")
        
        # Start the SSE listener in a background task
        stream_task_obj = asyncio.create_task(stream_task(client))
        
        # Give the stream a moment to connect
        await asyncio.sleep(0.5)
        
        # Interactive message loop
        print(f"\n✓ Connected as '{USERNAME}'")
        print("Commands:")
        print("  send   - Send a message")
        print("  history - View message history")
        print("  quit   - Exit")
        print()
        
        try:
            while True:
                command = input(f"{USERNAME}: ").strip().lower()
                
                if command == "quit":
                    print("Goodbye!")
                    break
                elif command == "send":
                    await send_message(client)
                elif command == "history":
                    await fetch_messages(client)
                elif command == "":
                    pass
                else:
                    print("Unknown command. Type 'send', 'history', or 'quit'.")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
        finally:
            stream_task_obj.cancel()
            try:
                await stream_task_obj
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
