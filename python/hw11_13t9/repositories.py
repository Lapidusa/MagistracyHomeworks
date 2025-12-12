from typing import Optional

from sqlalchemy.orm import Session

from .models import Student


class StudentsRepository:
  def __init__(self, db: Session):
    self.db = db

  def create(self, data) -> Student:
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

  def update(self, student_id: int, data) -> type[Student] | None:
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
