from typing import Optional, List

from pydantic import BaseModel, Field


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


class UserRegister(BaseModel):
  username: str = Field(..., min_length=3, example="admin")
  password: str = Field(..., min_length=4, example="qwerty")
  is_readonly: bool = Field(False, description="Если True — только чтение")


class UserLogin(BaseModel):
  username: str
  password: str


class TokenPairOut(BaseModel):
  access_token: str
  refresh_token: str
  token_type: str = "bearer"


class RefreshIn(BaseModel):
  refresh_token: str


class MessageOut(BaseModel):
  detail: str
