from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User, Token
from schemas import (
    UserRegister,
    UserLogin,
    TokenPairOut,
    MessageOut,
    RefreshIn,
)
from security import (
    hash_password,
    verify_password,
    generate_token_pair,
    now_utc,
    ACCESS_TOKEN_LIFETIME_MINUTES,
    REFRESH_TOKEN_LIFETIME_DAYS,
    get_current_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: UserRegister,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_readonly=payload.is_readonly,
        is_active=True,
    )
    db.add(user)
    db.commit()

    return MessageOut(detail="User registered successfully")


@router.post(
    "/login",
    response_model=TokenPairOut,
)
def login_user(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # деактивируем старые токены
    db.query(Token).filter(Token.user_id == user.id).update(
        {"is_active": False},
        synchronize_session=False,
    )

    access_token, refresh_token = generate_token_pair()
    token_obj = Token(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=now_utc() + timedelta(
            minutes=ACCESS_TOKEN_LIFETIME_MINUTES
        ),
        refresh_expires_at=now_utc() + timedelta(
            days=REFRESH_TOKEN_LIFETIME_DAYS
        ),
        is_active=True,
    )
    db.add(token_obj)
    db.commit()

    return TokenPairOut(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenPairOut,
)
def refresh_tokens(
    payload: RefreshIn,
    db: Session = Depends(get_db),
):
    token_obj = (
        db.query(Token)
        .filter(
            Token.refresh_token == payload.refresh_token,
            Token.is_active == True,  # noqa: E712
        )
        .first()
    )
    if (
        not token_obj
        or token_obj.refresh_expires_at < now_utc()
        or not token_obj.user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token, refresh_token = generate_token_pair()
    token_obj.access_token = access_token
    token_obj.refresh_token = refresh_token
    token_obj.access_expires_at = now_utc() + timedelta(
        minutes=ACCESS_TOKEN_LIFETIME_MINUTES
    )
    token_obj.refresh_expires_at = now_utc() + timedelta(
        days=REFRESH_TOKEN_LIFETIME_DAYS
    )

    db.commit()

    return TokenPairOut(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/logout",
    response_model=MessageOut,
)
def logout(
    token_obj: Token = Depends(get_current_token),
    db: Session = Depends(get_db),
):
    token_obj.is_active = False
    db.commit()
    return MessageOut(detail="Logged out successfully")
