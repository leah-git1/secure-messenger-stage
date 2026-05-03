"""
routes.py — All API route handlers.

╔══════════════════════════════════════════════╗
║  YOUR TASK: implement the four routes.       ║
╚══════════════════════════════════════════════╝

WHY A SEPARATE routes.py?
  In real projects, main.py only creates the app and wires things together.
  The actual logic lives in dedicated files — one per feature area.
  This keeps files small, focused, and easy to navigate.
  main.py imports this router and registers it with one line.

THE FOUR ROUTES YOU NEED TO IMPLEMENT:

  ┌─────────────────────────────────────────────────────────────────────┐
  │ POST /register                                                      │
  │   Receives: RegisterRequest (username, password)                    │
  │   1. Check if the username is already taken → return 400 if so     │
  │   2. Hash the password (NEVER store plain text)                     │
  │   3. Save the new User to the database                              │
  │   4. Return a success message                                       │
  └─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │ POST /login                                                         │
  │   Receives: LoginRequest (username, password)                       │
  │   1. Find the user in the database → return 401 if not found       │
  │   2. Verify the password against the stored hash → 401 if wrong    │
  │   3. Create and return a JWT token                                  │
  └─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │ POST /messages                          [requires valid JWT]        │
  │   Receives: SendMessageRequest (content, recipient)                 │
  │   1. Encrypt the content with encrypt()                             │
  │   2. Save a new Message row (sender=current user, recipient=...)    │
  │   3. Return the message as MessageResponse (with decrypted content) │
  └─────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────┐
  │ GET /messages                           [requires valid JWT]        │
  │   1. Fetch all messages from the database                           │
  │   2. Decrypt each message's ciphertext before returning             │
  │   3. Return a list of MessageResponse objects                       │
  │                                                                     │
  │   THINK ABOUT: should a user see ALL messages, or only those        │
  │   where they are the sender or recipient?                           │
  └─────────────────────────────────────────────────────────────────────┘

USEFUL IMPORTS ALREADY PROVIDED BELOW.
USEFUL PATTERN — how to query the database:
  user = db.query(User).filter(User.username == "alice").first()
  messages = db.query(Message).order_by(Message.created_at).all()

USEFUL PATTERN — how to save a new row:
  new_user = User(username="alice", password_hash="$2b$...")
  db.add(new_user)
  db.commit()
  db.refresh(new_user)   ← fills in the auto-generated id and created_at
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .models import User, Message, get_db
from .schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    SendMessageRequest, MessageResponse,
)
from .auth import hash_password, verify_password, create_token, require_auth
from .crypto import encrypt, decrypt

log = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# TODO 1 — Register a new user
# ---------------------------------------------------------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """
    רושם משתמש חדש במערכת לאחר בדיקה שהשם אינו תפוס ושמירת סיסמה מוצפנת (Hash).
    """
    # 1. בדיקה האם שם המשתמש כבר קיים במסד הנתונים
    existing_user = db.query(User).filter(User.username == body.username).first()
    if existing_user:
        log.warning(f"Registration failed: username {body.username} already taken")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # 2. יצירת "טביעת אצבע" לסיסמה (Hashing) - לעולם לא שומרים טקסט גלוי
    hashed_pwd = hash_password(body.password)

    # 3. שמירת המשתמש החדש
    new_user = User(username=body.username, password_hash=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log.info(f"User {body.username} registered successfully")
    return {"message": "User created successfully"}


# ---------------------------------------------------------------------------
# TODO 2 — Login and receive a JWT token
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """
    מאמת את פרטי המשתמש ומנפיק תג (JWT) לשימוש עתידי.
    """
    # 1. חיפוש המשתמש במסד הנתונים
    user = db.query(User).filter(User.username == body.username).first()
    
    # 2. אימות המשתמש והסיסמה (בדיקת ה-Hash)
    if not user or not verify_password(body.password, user.password_hash):
        log.warning(f"Login failed for user: {body.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # 3. יצירת ה-Token (החתימה הדיגיטלית)
    access_token = create_token(username=user.username)
    
    log.info(f"User {body.username} logged in")
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# TODO 3 — Send a message (authenticated)
# ---------------------------------------------------------------------------
@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    body: SendMessageRequest,
    db: Session = Depends(get_db),
    username: str = Depends(require_auth),
):
    """
    שולח הודעה מוצפנת ממשתמש מאומת לנמען מסוים.
    """
    # 1. הצפנת תוכן ההודעה (AES-256-GCM)
    ciphertext = encrypt(body.content)

    # 2. שמירת ההודעה המוצפנת במסד הנתונים
    new_message = Message(
        sender=username,
        recipient=body.recipient,
        ciphertext=ciphertext
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # 3. החזרת ההודעה עם תוכן מפוענח לצורך תצוגה מיידית למשתמש השולח
    return MessageResponse(
        id=new_message.id,
        sender=new_message.sender,
        recipient=new_message.recipient,
        content=body.content,  # מחזירים את הטקסט המקורי
        created_at=new_message.created_at
    )


# ---------------------------------------------------------------------------
# TODO 4 — Fetch messages (authenticated)
# ---------------------------------------------------------------------------
@router.get("/messages", response_model=list[MessageResponse])
def get_messages(
    db: Session = Depends(get_db),
    username: str = Depends(require_auth),
):
    """
    שולף את כל ההודעות שבהן המשתמש הנוכחי הוא השולח או הנמען, ומפענח אותן.
    """
    # 1. שליפת הודעות הרלוונטיות למשתמש בלבד (אבטחה בסיסית)
    messages = db.query(Message).filter(
        (Message.sender == username) | (Message.recipient == username)
    ).order_by(Message.created_at.asc()).all()

    # 2. פענוח כל הודעה לפני החזרתה
    decrypted_messages = []
    for msg in messages:
        try:
            plain_text = decrypt(msg.ciphertext)
            decrypted_messages.append(MessageResponse(
                id=msg.id,
                sender=msg.sender,
                recipient=msg.recipient,
                content=plain_text,
                created_at=msg.created_at
            ))
        except Exception as e:
            log.error(f"Failed to decrypt message ID {msg.id}: {e}")
            # במקרה של כשל בפענוח, נדלג על ההודעה או נחזיר שגיאה (תלוי במדיניות האבטחה)
            continue

    return decrypted_messages