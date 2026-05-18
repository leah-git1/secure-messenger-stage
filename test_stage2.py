#!/usr/bin/env python3
"""
test_stage2.py — Test Stage 2 SSE and real-time messaging
"""

import httpx
import asyncio
import json


BASE_URL = "http://localhost:8000"


async def test_stage2():
    """Test the SSE streaming feature."""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧪 Testing Stage 2 - Real-time Messaging with SSE\n")
        
        # 1. Register two users
        print("1️⃣ Registering alice and bob...")
        for user in ["alice", "bob"]:
            try:
                resp = await client.post(
                    f"{BASE_URL}/register",
                    json={"username": user, "password": "password123"},
                )
                resp.raise_for_status()
                print(f"   ✓ {user} registered")
            except Exception as e:
                print(f"   ℹ️ {user} might already exist: {e}")
        
        # 2. Login as bob
        print("\n2️⃣ Logging in as bob...")
        resp = await client.post(
            f"{BASE_URL}/login",
            json={"username": "bob", "password": "password123"},
        )
        bob_token = resp.json()["access_token"]
        print(f"   ✓ Bob's token: {bob_token[:20]}...")
        
        # 3. Login as alice
        print("\n3️⃣ Logging in as alice...")
        resp = await client.post(
            f"{BASE_URL}/login",
            json={"username": "alice", "password": "password123"},
        )
        alice_token = resp.json()["access_token"]
        print(f"   ✓ Alice's token: {alice_token[:20]}...")
        
        # 4. Start listening to bob's stream in a background task
        print("\n4️⃣ Starting SSE stream listener for bob...")
        received_messages = []
        
        async def listen_bob_stream():
            headers = {"Authorization": f"Bearer {bob_token}"}
            try:
                async with client.stream(
                    "GET",
                    f"{BASE_URL}/stream",
                    headers=headers,
                    timeout=10,
                ) as response:
                    print("   ✓ Stream connected for bob")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            msg = json.loads(line[6:])
                            received_messages.append(msg)
                            print(f"   📨 Bob received: {msg}")
            except asyncio.TimeoutError:
                print("   ⏱️ Stream timeout (expected after test)")
            except Exception as e:
                print(f"   ℹ️ Stream closed: {e}")
        
        # Start the listener
        listener_task = asyncio.create_task(listen_bob_stream())
        await asyncio.sleep(1)  # Give it a moment to connect
        
        # 5. Alice sends a message to bob
        print("\n5️⃣ Alice sending message to bob...")
        headers = {"Authorization": f"Bearer {alice_token}"}
        resp = await client.post(
            f"{BASE_URL}/messages",
            json={"content": "Hello Bob! 🎉", "recipient": "bob"},
            headers=headers,
        )
        sent_msg = resp.json()
        print(f"   ✓ Message sent: {sent_msg}")
        
        # Wait a bit for the message to arrive through the stream
        await asyncio.sleep(1)
        
        # 6. Cancel the listener and check if we got the message
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
        
        # 7. Verify
        print("\n6️⃣ Verification:")
        if received_messages:
            print(f"   ✅ SUCCESS! Bob received message through SSE stream!")
            print(f"   Message: {received_messages[0]}")
        else:
            print(f"   ⚠️ No messages received through stream")
        
        # 8. Test GET /messages endpoint
        print("\n7️⃣ Testing GET /messages (fetch history)...")
        resp = await client.get(
            f"{BASE_URL}/messages",
            headers=headers,
        )
        messages = resp.json()
        print(f"   ✓ Fetched {len(messages)} messages")
        for msg in messages:
            print(f"   - {msg['sender']} → {msg['recipient']}: {msg['content']}")
        
        print("\n✅ Stage 2 test complete!\n")


if __name__ == "__main__":
    asyncio.run(test_stage2())
