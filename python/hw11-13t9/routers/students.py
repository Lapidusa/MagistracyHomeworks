from typing import List

import csv
import json

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from database import get_db, SessionLocal
from models import Student
from repositories import StudentsRepository
from schemas import (
    StudentCreate,
    StudentUpdate,
    StudentOut,
    MessageOut,
    CSVImportRequest,
    BulkDeleteRequest,
)
from security import get_current_user, require_write_user
from cache import redis_client, invalidate_students_cache
from sqlalchemy.orm import Session
from sqlalchemy import delete as sa_delete


router = APIRouter(prefix="/students", tags=["students"])


def get_students_repo(db=Depends(get_db)) -> StudentsRepository:
  return StudentsRepository(db)

def import_students_from_csv_task(csv_path: str) -> None:
  db: Session = SessionLocal()
  try:
    with open(csv_path, "r", encoding="utf-8-sig") as f:
      reader = csv.DictReader(f, delimiter=",")

      for row in reader:
        if not row.get("Фамилия") or not row.get("Имя"):
          continue

        course_name = (row.get("Курс") or "").strip()
        if not course_name:
          continue

        try:
          grade = float(row["Оценка"])
        except (ValueError, TypeError, KeyError):
          continue

        student = Student(
          last_name=row["Фамилия"].strip(),
          first_name=row["Имя"].strip(),
          faculty=(row.get("Факультет") or "").strip(),
          course=course_name,
          grade=grade,
        )
        db.add(student)

      db.commit()

    invalidate_students_cache()
  finally:
    db.close()


def bulk_delete_students_task(ids: List[int]) -> None:
  if not ids:
    return

  db: Session = SessionLocal()
  try:
    stmt = sa_delete(Student).where(Student.id.in_(ids))
    db.execute(stmt)
    db.commit()

    invalidate_students_cache()
  finally:
    db.close()

@router.post(
  "/import-csv",
  response_model=MessageOut,
  status_code=status.HTTP_202_ACCEPTED,
)
def import_students_from_csv(
  payload: CSVImportRequest,
  background_tasks: BackgroundTasks,
  user=Depends(require_write_user),
):
  background_tasks.add_task(import_students_from_csv_task, payload.path)
  return MessageOut(detail=f"CSV import scheduled for path: {payload.path}")


@router.post(
  "/bulk-delete",
  response_model=MessageOut,
  status_code=status.HTTP_202_ACCEPTED,
)
def bulk_delete_students(
  payload: BulkDeleteRequest,
  background_tasks: BackgroundTasks,
  user=Depends(require_write_user),
):
  if not payload.ids:
    return MessageOut(detail="No IDs provided, nothing to delete")

  background_tasks.add_task(bulk_delete_students_task, payload.ids)
  return MessageOut(detail=f"Bulk delete scheduled for ids: {payload.ids}")


@router.post(
  "",
  response_model=StudentOut,
  status_code=status.HTTP_201_CREATED,
)
def create_student(
  payload: StudentCreate,
  repo: StudentsRepository = Depends(get_students_repo),
  user=Depends(require_write_user),
):
  student = repo.create(payload)
  # после изменения данных — чистим кеш
  invalidate_students_cache()
  return student


@router.get(
  "",
  response_model=List[StudentOut],
)
def list_students(
  repo: StudentsRepository = Depends(get_students_repo),
  user=Depends(get_current_user),
):
  cache_key = "students:list"
  cached = redis_client.get(cache_key)
  if cached:
    return json.loads(cached)

  students = repo.list()
  data = [
    StudentOut.model_validate(s).model_dump(mode="json") for s in students
  ]

  redis_client.setex(cache_key, 60, json.dumps(data, ensure_ascii=False))
  return data


@router.get(
  "/{student_id}",
  response_model=StudentOut,
)
def get_student(
  student_id: int,
  repo: StudentsRepository = Depends(get_students_repo),
  user=Depends(get_current_user),
):
  cache_key = f"students:{student_id}"
  cached = redis_client.get(cache_key)
  if cached:
    return json.loads(cached)

  student = repo.get(student_id)
  if not student:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Student not found",
    )

  data = StudentOut.model_validate(student).model_dump(mode="json")
  redis_client.setex(cache_key, 60, json.dumps(data, ensure_ascii=False))
  return data


@router.put(
  "/{student_id}",
  response_model=StudentOut,
)
def update_student(
  student_id: int,
  payload: StudentUpdate,
  repo: StudentsRepository = Depends(get_students_repo),
  user=Depends(require_write_user),
):
  student = repo.update(student_id, payload)
  if not student:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Student not found",
    )

  invalidate_students_cache()
  return student


@router.delete(
  "/{student_id}",
  status_code=status.HTTP_204_NO_CONTENT,
)
def delete_student(
  student_id: int,
  repo: StudentsRepository = Depends(get_students_repo),
  user=Depends(require_write_user),
):
  ok = repo.delete(student_id)
  if not ok:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Student not found",
    )

  invalidate_students_cache()
  return None