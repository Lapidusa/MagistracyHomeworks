from typing import List, Optional, Any, Generator

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Float, Integer
from sqlalchemy.orm import declarative_base, mapped_column, sessionmaker, Session

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

class Student(Base):

  __tablename__ = "students"

  id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
  last_name = mapped_column(String(100), nullable=False)
  first_name = mapped_column(String(100), nullable=False)
  faculty = mapped_column(String(100), nullable=False)
  course = mapped_column(String(100), nullable=False)
  grade = mapped_column(Float, nullable=False)

class StudentBase(BaseModel):
  last_name: str = Field(..., example="Иванов")
  first_name: str = Field(..., example="Пётр")
  faculty: str = Field(..., example="ФПМИ")
  course: str = Field(..., example="Мат. Анализ")
  grade: float = Field(..., ge=0, le=100, example=75)


class StudentCreate(StudentBase):
  pass


class StudentUpdate(BaseModel):

  last_name: Optional[str] = None
  first_name: Optional[str] = None
  faculty: Optional[str] = None
  course: Optional[str] = None
  grade: Optional[float] = Field(None, ge=0, le=100)


class StudentOut(StudentBase):
  id: int

  class Config:
    orm_mode = True

class StudentsRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, data: StudentCreate) -> Student:
    student = Student(
      last_name=data.last_name,
      first_name=data.first_name,
      faculty=data.faculty,
      course=data.course,
      grade=data.grade,
    )
    self.db.add(student)
    self.db.commit()
    self.db.refresh(student)
    return student

  def get(self, student_id: int) -> Optional[Student]:
    return self.db.get(Student, student_id)

  def list(self) -> list[type[Student]]:
    return self.db.query(Student).all()

  def update(self, student_id: int, data: StudentUpdate) -> type[Student] | None:
    student = self.db.get(Student, student_id)
    if not student:
      return None

    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
      setattr(student, field, value)

    self.db.commit()
    self.db.refresh(student)
    return student

  def delete(self, student_id: int) -> bool:
    student = self.db.get(Student, student_id)
    if not student:
      return False

    self.db.delete(student)
    self.db.commit()
    return True

def get_db() -> Generator[Session, Any, None]:
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


def get_repo(db: Session = Depends(get_db)) -> StudentsRepository:
  return StudentsRepository(db)

app = FastAPI(
  title="Students CRUD API",
  description="Домашнее задание: REST API. Реализация CRUD на FastAPI",
  version="1.0.0",
)


@app.on_event("startup")
def on_startup():
  Base.metadata.create_all(bind=engine)

@app.post(
  "/students",
  response_model=StudentOut,
  status_code=status.HTTP_201_CREATED,
)
def create_student(
    payload: StudentCreate,
    repo: StudentsRepository = Depends(get_repo),
):
  student = repo.create(payload)
  return student


@app.get(
  "/students",
  response_model=List[StudentOut],
)
def list_students(
    repo: StudentsRepository = Depends(get_repo),
):
  students = repo.list()
  return students


@app.get(
  "/students/{student_id}",
  response_model=StudentOut,
)
def get_student(
    student_id: int,
    repo: StudentsRepository = Depends(get_repo),
):
  student = repo.get(student_id)
  if not student:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Student not found",
    )
  return student


@app.put(
  "/students/{student_id}",
  response_model=StudentOut,
)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    repo: StudentsRepository = Depends(get_repo),
):
  student = repo.update(student_id, payload)
  if not student:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Student not found",
    )
  return student


@app.delete(
  "/students/{student_id}",
  status_code=status.HTTP_204_NO_CONTENT,
)
def delete_student(
    student_id: int,
    repo: StudentsRepository = Depends(get_repo),
):
  ok = repo.delete(student_id)
  if not ok:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Student not found",
    )
  return None
