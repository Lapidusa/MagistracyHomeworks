from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from database import get_db
from repositories import StudentsRepository
from schemas import StudentCreate, StudentUpdate, StudentOut
from security import get_current_user, require_write_user

router = APIRouter(prefix="/students", tags=["students"])


def get_students_repo(db=Depends(get_db)) -> StudentsRepository:
  return StudentsRepository(db)


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
  return student


@router.get(
  "",
  response_model=List[StudentOut],
)
def list_students(
    repo: StudentsRepository = Depends(get_students_repo),
    user=Depends(get_current_user),
):
  return repo.list()


@router.get(
  "/{student_id}",
  response_model=StudentOut,
)
def get_student(
    student_id: int,
    repo: StudentsRepository = Depends(get_students_repo),
    user=Depends(get_current_user),
):
  student = repo.get(student_id)
  if not student:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Student not found",
    )
  return student


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
  return None
