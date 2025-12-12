from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hw11_13t9.database import Base, get_db
from hw11_13t9.models import User, Token, Student
from hw11_13t9.security import (
    hash_password,
    generate_token_pair,
    now_utc,
    ACCESS_TOKEN_LIFETIME_MINUTES,
    REFRESH_TOKEN_LIFETIME_DAYS,
    get_current_token,
    require_write_user,
)
from hw11_13t9.main import app

TEST_DB_URL = "sqlite:///./test_db.sqlite3"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

def override_require_write_user():
    class DummyUser:
        id = 1
        username = "writer"
        is_readonly = False
        is_active = True

    return DummyUser()


app.dependency_overrides[require_write_user] = override_require_write_user


def override_get_current_token():
    db = TestingSessionLocal()
    try:
        token_obj = (
            db.query(Token)
            .filter(Token.is_active == True)
            .order_by(Token.id.desc())
            .first()
        )
        if not token_obj:
            user = User(
                username="temp_user",
                password_hash=hash_password("temp"),
                is_readonly=False,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            access, refresh = generate_token_pair()
            token_obj = Token(
                user_id=user.id,
                access_token=access,
                refresh_token=refresh,
                access_expires_at=now_utc()
                                  + timedelta(minutes=ACCESS_TOKEN_LIFETIME_MINUTES),
                refresh_expires_at=now_utc()
                                   + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS),
                is_active=True,
            )
            db.add(token_obj)
            db.commit()
            db.refresh(token_obj)

        return token_obj
    finally:
        db.close()


app.dependency_overrides[get_current_token] = override_get_current_token


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    return TestClient(app)


def create_user(db, username="alice", password="secret", is_active=True):
    user = User(
        username=username,
        password_hash=hash_password(password),
        is_readonly=False,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_token_for_user(db, user: User):
    access, refresh = generate_token_pair()
    token = Token(
        user_id=user.id,
        access_token=access,
        refresh_token=refresh,
        access_expires_at=now_utc()
        + timedelta(minutes=ACCESS_TOKEN_LIFETIME_MINUTES),
        refresh_expires_at=now_utc()
        + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS),
        is_active=True,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def create_student(db, **kwargs):
    student = Student(
        last_name=kwargs.get("last_name", "Иванов"),
        first_name=kwargs.get("first_name", "Иван"),
        faculty=kwargs.get("faculty", "ФКН"),
        course=kwargs.get("course", "1"),
        grade=kwargs.get("grade", 4.5),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

def test_register_user_success(client, db):
    payload = {
        "username": "newuser",
        "password": "strongpass",
        "is_readonly": False,
    }
    resp = client.post("/auth/register", json=payload)

    assert resp.status_code == 201
    assert resp.json()["detail"] == "User registered successfully"

    assert db.query(User).filter_by(username="newuser").first() is not None


def test_register_user_duplicate_username(client, db):
    create_user(db, username="dup", password="pwd")

    payload = {
        "username": "dup",
        "password": "another",
        "is_readonly": False,
    }
    resp = client.post("/auth/register", json=payload)

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Username already exists"

def test_login_user_success(client, db):
    create_user(db, username="bob", password="secret123")

    resp = client.post(
        "/auth/login",
        json={"username": "bob", "password": "secret123"},
    )

    data = resp.json()
    assert resp.status_code == 200
    assert "access_token" in data
    assert "refresh_token" in data
    assert db.query(Token).count() == 1


def test_login_user_invalid_credentials(client, db):
    create_user(db, username="charlie", password="correct")

    resp = client.post(
        "/auth/login",
        json={"username": "charlie", "password": "wrong"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password"

def test_refresh_tokens_success(client, db):
    user = create_user(db, username="ref_user", password="pwd")
    token = create_token_for_user(db, user)

    resp = client.post(
        "/auth/refresh",
        json={"refresh_token": token.refresh_token},
    )

    data = resp.json()
    assert resp.status_code == 200
    assert "access_token" in data and "refresh_token" in data
    # новые токены должны отличаться от старых
    assert data["refresh_token"] != token.refresh_token


def test_refresh_tokens_invalid_refresh_token(client):
    resp = client.post(
        "/auth/refresh",
        json={"refresh_token": "non-existing-token"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or expired refresh token"


# --------- /auth/logout ---------


def test_logout_deactivates_token(client, db):
    user = create_user(db, username="logout_user", password="pwd")
    token = create_token_for_user(db, user)

    # будет использована заглушка override_get_current_token,
    # которая вернёт первый активный токен
    resp = client.post("/auth/logout")

    assert resp.status_code == 200
    assert resp.json()["detail"] == "Logged out successfully"

    db.refresh(token)
    assert token.is_active is False


def test_logout_idempotent(client, db):
    user = create_user(db, username="logout2", password="pwd")
    token = create_token_for_user(db, user)

    client.post("/auth/logout")
    db.refresh(token)
    assert token.is_active is False

    # второй вызов не должен падать
    resp2 = client.post("/auth/logout")
    assert resp2.status_code == 200


# --------- /students  (POST /students) ---------


def test_create_student_success(client, db):
    payload = {
        "last_name": "Петров",
        "first_name": "Пётр",
        "faculty": "ФИВТ",
        "course": "2",
        "grade": 4.7,
    }

    resp = client.post("/students", json=payload)
    data = resp.json()

    assert resp.status_code == 201
    assert data["last_name"] == "Петров"
    assert data["first_name"] == "Пётр"

    assert db.query(Student).filter_by(last_name="Петров").first() is not None


def test_create_student_validation_error(client):
    # grade некорректный (например, отрицательный), ждём 422 от Pydantic
    payload = {
        "last_name": "Ошибка",
        "first_name": "Тест",
        "faculty": "ФИВТ",
        "course": "1",
        "grade": -1.0,
    }

    resp = client.post("/students", json=payload)
    assert resp.status_code == 422


# --------- /students/{id}  (PUT) ---------


def test_update_student_success(client, db):
    student = create_student(db, last_name="Сидоров", grade=3.5)

    payload = {
        "last_name": "Сидоров",
        "first_name": "Илья",
        "faculty": "ФНБ",
        "course": "3",
        "grade": 4.0,
    }

    resp = client.put(f"/students/{student.id}", json=payload)
    data = resp.json()

    assert resp.status_code == 200
    assert data["first_name"] == "Илья"
    assert data["grade"] == 4.0


def test_update_student_not_found(client):
    payload = {
        "last_name": "Нет",
        "first_name": "Такого",
        "faculty": "ФКН",
        "course": "1",
        "grade": 4.0,
    }

    resp = client.put("/students/99999", json=payload)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Student not found"
