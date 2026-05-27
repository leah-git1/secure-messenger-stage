"""
seed.py — Populate the database with test data.
Run: python seed.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from server.models import Base, User, Message, get_db, engine
from server.auth import hash_password
from server.crypto import encrypt

# Wipe and recreate tables
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = next(get_db())

users = [
    ("alice", "password123"),
    ("bob",   "password123"),
    ("charlie", "password123"),
]

for username, password in users:
    db.add(User(username=username, password_hash=hash_password(password)))
db.commit()

messages = [
    ("alice",   "bob",     "Hey Bob, how are you?"),
    ("bob",     "alice",   "All good! You?"),
    ("alice",   "charlie", "Charlie, meeting at 3pm?"),
    ("charlie", "alice",   "Sure, see you then!"),
    ("bob",     "charlie", "Charlie, did you get Alice's message?"),
]

for sender, recipient, content in messages:
    db.add(Message(sender=sender, recipient=recipient, ciphertext=encrypt(content)))
db.commit()
db.close()

print(f"Seeded {len(users)} users and {len(messages)} messages.")
