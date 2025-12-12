from sqlalchemy import String, Float, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import mapped_column, relationship

from .database import Base


class Student(Base):
  __tablename__ = "students"

  id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
  last_name = mapped_column(String(100), nullable=False)
  first_name = mapped_column(String(100), nullable=False)
  faculty = mapped_column(String(100), nullable=False)
  course = mapped_column(String(100), nullable=False)
  grade = mapped_column(Float, nullable=False)


class User(Base):
  __tablename__ = "users"

  id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
  username = mapped_column(String(100), unique=True, nullable=False, index=True)
  password_hash = mapped_column(String(256), nullable=False)
  is_readonly = mapped_column(Boolean, default=False, nullable=False)
  is_active = mapped_column(Boolean, default=True, nullable=False)

  tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")


class Token(Base):
  __tablename__ = "tokens"

  id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
  user_id = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

  access_token = mapped_column(String(255), unique=True, index=True, nullable=False)
  refresh_token = mapped_column(String(255), unique=True, index=True, nullable=False)

  access_expires_at = mapped_column(DateTime, nullable=False)
  refresh_expires_at = mapped_column(DateTime, nullable=False)

  is_active = mapped_column(Boolean, default=True, nullable=False)

  user = relationship("User", back_populates="tokens")
