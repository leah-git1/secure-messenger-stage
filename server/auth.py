"""
auth.py — Password hashing and JWT token logic.

╔══════════════════════════════════════════════╗
║  YOUR TASK: implement the five functions.    ║
╚══════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCEPT 1 — WHY WE HASH PASSWORDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Imagine every password in your database was stored as plain text.
  One database leak → every user's password is exposed, forever.

  bcrypt solves this by being a ONE-WAY function:
    hash("secret123") → "$2b$12$eImiTXuW..." (a fingerprint)
    There is no reverse. The original password is gone.

  When a user logs in, we don't un-hash. Instead we re-hash the
  typed password and compare the two fingerprints. If they match —
  the password was correct, without ever knowing the original.

  bcrypt is also INTENTIONALLY SLOW (has a "cost factor").
  Even if someone steals your DB, brute-forcing takes years.

  Use:
    import bcrypt
    hash  = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    match = bcrypt.checkpw(password.encode(), stored_hash.encode())

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCEPT 2 — WHY WE USE JWT TOKENS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  After a successful login, the server gives the client a JWT token.
  Think of it as a signed wristband at a concert:
    - It proves you paid (authenticated) without checking your ID again
    - It has an expiry date printed on it
    - The bouncer (server) can verify it's real by checking the signature
    - The server never needs to look up a database to validate it

  A JWT has three parts, separated by dots:
    header.payload.signature
    eyJhbGc...  .eyJzdWI...  .SflKxw...

  The payload contains the username and expiry time — readable but
  tamper-proof (changing anything breaks the signature).

  Use:
    from jose import jwt, JWTError
    token   = jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm="HS256")
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCEPT 3 — FASTAPI DEPENDENCY INJECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  require_auth() is a FastAPI "dependency". Instead of copy-pasting
  token validation into every route, you declare it once here and
  inject it into any route that needs it:

    @router.get("/messages")
    def get_messages(username: str = Depends(require_auth)):
        # username is already validated — if we got here, the token was valid
        ...

  FastAPI calls require_auth() automatically before your route runs.
  If the token is missing or invalid, it raises HTTP 401 and your
  route never executes.

  The HTTPBearer() helper extracts the token from the header:
    Authorization: Bearer eyJhbGc...
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


SECRET_KEY = "change-this-to-a-long-random-string-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# TODO 1 — Hash a plain-text password with bcrypt
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    """
    הופך סיסמה גלויה ל-Hash מאובטח באמצעות bcrypt.
    מייצר Salt רנדומלי לכל סיסמה כדי למנוע התקפות Rainbow Table.
    """
    # המרת הטקסט לבייטים (Bytes) לצורך עבודה עם bcrypt
    pwd_bytes = plain.encode('utf-8')
    # יצירת מלח (Salt) וביצוע Hashing
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    # החזרה כמחרוזת (String) לצורך שמירה ב-Database
    return hashed_password.decode('utf-8')


# ---------------------------------------------------------------------------
# TODO 2 — Check a plain-text password against a stored bcrypt hash
# ---------------------------------------------------------------------------
def verify_password(plain: str, hashed: str) -> bool:
    """
    בודק האם סיסמה שהוזנה תואמת ל-Hash ששמור בבסיס הנתונים.
    """
    # המרת שני הערכים לבייטים לצורך השוואה בטוחה
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


# ---------------------------------------------------------------------------
# TODO 3 — Create a signed JWT token for a given username
# ---------------------------------------------------------------------------
def create_token(username: str) -> str:
    """
    מייצר Payload שכולל את שם המשתמש וזמן תפוגה, וחותם אותו עם SECRET_KEY.
    """
    # קביעת זמן התפוגה
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    
    # בניית גוף ההודעה (Payload) - "sub" הוא הסטנדרט לשם המשתמש/מזהה
    to_encode = {
        "sub": username,
        "exp": expire
    }
    
    # חתימת ה-Token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ---------------------------------------------------------------------------
# TODO 4 — Decode and validate a JWT token
# ---------------------------------------------------------------------------
def decode_token(token: str) -> Optional[str]:
    """
    מפענח את ה-Token ובודק את תקינות החתימה והתפוגה.
    מחזיר את שם המשתמש (sub) במידה ותקין, אחרת None.
    """
    try:
        # הפענוח בודק אוטומטית את החתימה ואת זמן התפוגה (exp)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            return None
        return username
    except JWTError:
        # אם ה-Token פג תוקף או שונה ע"י גורם זר, תיזרק שגיאה
        return None


# ---------------------------------------------------------------------------
# TODO 5 — FastAPI dependency: enforce authentication on a route
# ---------------------------------------------------------------------------
def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """
    Dependency שמוודא קיום Token תקף ב-Header של הבקשה.
    תומך גם בטוקן via query parameter (?token=...) לצורך SSE/EventSource.
    אם הטוקן לא תקין, זורק שגיאת 401 ועוצר את המשך הבקשה.
    """
    # חילוץ מחרוזת ה-Token מתוך ה-Bearer
    token = credentials.credentials if credentials else None
    
    # ניסיון פענוח
    username = decode_token(token) if token else None
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # החזרת שם המשתמש שישמש את ה-Route
    return username


async def require_auth_with_query(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    request: Request = None,
) -> str:
    """
    Enhanced auth dependency supporting both header and query parameter tokens.
    Used for SSE endpoints where JavaScript EventSource can't set custom headers.
    
    Order of precedence:
    1. Authorization header (Bearer token)
    2. ?token=<jwt> query parameter
    """
    token = None
    
    # Try header first
    if credentials:
        token = credentials.credentials
    # Try query parameter (for SSE/EventSource)
    elif request:
        token = request.query_params.get("token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = decode_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return username