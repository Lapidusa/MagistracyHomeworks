from typing import Generator, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

DATABASE_URL = "sqlite:///../hw9t9/students.db"

engine = create_engine(
  DATABASE_URL,
  echo=False,
  future=True,
)

SessionLocal = sessionmaker(
  bind=engine,
  autoflush=False,
  autocommit=False,
)

Base = declarative_base()


def get_db() -> Generator[Session, Any, None]:
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()
