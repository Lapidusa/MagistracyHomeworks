import csv
from dataclasses import dataclass
from typing import List, Set, Optional

from sqlalchemy import (
    create_engine,
    Integer,
    String,
    Float,
    select,
    func,
)
from sqlalchemy.orm import declarative_base, Session, mapped_column

Base = declarative_base()


class Student(Base):
    __tablename__ = "students"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    last_name = mapped_column(String(100), nullable=False)
    first_name = mapped_column(String(100), nullable=False)
    faculty = mapped_column(String(100), nullable=False)
    course = mapped_column(String(100), nullable=False)
    grade = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:
        return (
            f"Student(id={self.id}, "
            f"{self.last_name} {self.first_name}, "
            f"faculty={self.faculty}, course={self.course}, grade={self.grade})"
        )


@dataclass
class StudentDTO:
    last_name: str
    first_name: str
    faculty: str
    course: str
    grade: float


class StudentsRepository:
    def __init__(self, db_url: str = "sqlite:///students.db") -> None:
        self.engine = create_engine(db_url, echo=False, future=True)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def add_student(
        self,
        last_name: str,
        first_name: str,
        faculty: str,
        course: str,
        grade: float,
    ) -> None:
        with Session(self.engine) as session:
            student = Student(
                last_name=last_name,
                first_name=first_name,
                faculty=faculty,
                course=course,
                grade=grade,
            )
            session.add(student)
            session.commit()

    def get_all_students(self) -> List[StudentDTO]:
        with Session(self.engine) as session:
            stmt = select(Student)
            rows = session.execute(stmt).scalars().all()
            return [
                StudentDTO(
                    last_name=s.last_name,
                    first_name=s.first_name,
                    faculty=s.faculty,
                    course=s.course,
                    grade=s.grade,
                )
                for s in rows
            ]

    def load_from_csv(self, csv_path: str) -> None:
        with Session(self.engine) as session, open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=",")

            for row in reader:
                if not row.get("Фамилия") or not row.get("Имя"):
                    continue

                course_name = (row.get("Курс") or "").strip()
                if not course_name:
                    continue

                try:
                    grade = float(row["Оценка"])
                except (ValueError, TypeError):
                    continue

                student = Student(
                    last_name=row["Фамилия"].strip(),
                    first_name=row["Имя"].strip(),
                    faculty=row["Факультет"].strip(),
                    course=course_name,
                    grade=grade,
                )
                session.add(student)

            session.commit()

    def get_students_by_faculty(self, faculty_name: str) -> List[StudentDTO]:

        with Session(self.engine) as session:
            stmt = select(Student).where(Student.faculty == faculty_name)
            rows = session.execute(stmt).scalars().all()
            return [
                StudentDTO(
                    last_name=s.last_name,
                    first_name=s.first_name,
                    faculty=s.faculty,
                    course=s.course,
                    grade=s.grade,
                )
                for s in rows
            ]

    def get_unique_courses(self) -> Set[int]:

        with Session(self.engine) as session:
            stmt = select(Student.course).distinct()
            rows = session.execute(stmt).scalars().all()
            return set(rows)

    def get_average_grade_by_faculty(self, faculty_name: str) -> Optional[float]:

        with Session(self.engine) as session:
            stmt = select(func.avg(Student.grade)).where(Student.faculty == faculty_name)
            avg_value = session.execute(stmt).scalar()
            return float(avg_value) if avg_value is not None else None

    def get_students_by_course_with_grade_below(
        self,
        course: str,
        max_grade: float = 30.0,
    ) -> List[StudentDTO]:
        with Session(self.engine) as session:
            stmt = (
                select(Student)
                .where(Student.course == course)
                .where(Student.grade < max_grade)
            )
            rows = session.execute(stmt).scalars().all()
            return [
                StudentDTO(
                    last_name=s.last_name,
                    first_name=s.first_name,
                    faculty=s.faculty,
                    course=s.course,
                    grade=s.grade,
                )
                for s in rows
            ]

def main():
    repo = StudentsRepository("sqlite:///students.db")

    repo.create_schema()

    repo.load_from_csv("students.csv")

    print("=== Все студенты ===")
    for s in repo.get_all_students():
        print(s)

    print("\n=== Студенты ФПМИ ===")
    for s in repo.get_students_by_faculty("ФПМИ"):
        print(s)

    print("\n=== Уникальные курсы ===")
    print(repo.get_unique_courses())

    print("\n=== Средний балл по факультету ФПМИ ===")
    print(repo.get_average_grade_by_faculty("ФПМИ"))

    print("\n=== Студенты по курсу 'Мат. Анализ' с оценкой < 30 ===")
    for s in repo.get_students_by_course_with_grade_below("Мат. Анализ", max_grade=30):
        print(s)


if __name__ == "__main__":
    main()
