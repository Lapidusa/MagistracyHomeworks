from datetime import datetime
import hashlib
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from .database import get_db
from hw11_13t9.models import Token, User

PASSWORD_SALT = "very-secret-salt-for-homework"

ACCESS_TOKEN_LIFETIME_MINUTES = 15
REFRESH_TOKEN_LIFETIME_DAYS = 7


def now_utc() -> datetime:
  return datetime.utcnow()


def hash_password(raw: str) -> str:
  data = (PASSWORD_SALT + raw).encode("utf-8")
  return hashlib.sha256(data).hexdigest()


def verify_password(raw: str, hashed: str) -> bool:
  return hash_password(raw) == hashed


def generate_token_pair() -> tuple[str, str]:
  access = secrets.token_urlsafe(32)
  refresh = secrets.token_urlsafe(48)
  return access, refresh


def get_current_token(
  request: Request,
  db: Session = Depends(get_db),
  access_token_q: Optional[str] = Query(
    default=None,
    alias="access_token",
    description="Access token as query param (fallback if no Authorization header)",
  ),
) -> Token:
  auth_header = request.headers.get("Authorization")

  token_str: Optional[str] = None

  if auth_header and auth_header.startswith("Bearer "):
    token_str = auth_header.split(" ", 1)[1].strip()

  if not token_str and access_token_q:
    token_str = access_token_q.strip()

  if not token_str:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Missing access token (use Authorization: Bearer <token> or ?access_token=)",
    )

  token_obj: Optional[Token] = (
    db.query(Token)
    .filter(
      Token.access_token == token_str,
      Token.is_active == True,  # noqa: E712
    )
    .first()
  )

  if not token_obj or token_obj.access_expires_at < now_utc():
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Token expired or invalid",
    )

  if not token_obj.user.is_active:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="User is inactive",
    )

  return token_obj


def get_current_user(token: Token = Depends(get_current_token)) -> User:
  return token.user


def require_write_user(user: User = Depends(get_current_user)) -> User:
  if user.is_readonly:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Read-only user cannot modify data",
    )
  return user
