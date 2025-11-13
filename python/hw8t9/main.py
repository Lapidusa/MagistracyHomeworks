from enum import Enum
from pathlib import Path
from datetime import date, datetime, timezone
import json
import re
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, validator


app = FastAPI(
    title="Support Requests",
    description="Домашка: сервис для сбора обращений абонентов",
)

class ReasonEnum(str, Enum):
    no_internet = "нет доступа к сети"
    phone_broken = "не работает телефон"
    no_emails = "не приходят письма"


class SupportRequest(BaseModel):
    last_name: str
    first_name: str
    birth_date: date
    phone: str
    email: EmailStr

    reasons: List[ReasonEnum] = []

    problem_found_at: Optional[datetime] = None

    @validator("last_name", "first_name")
    def validate_name(cls, v: str) -> str:

        v = v.strip()
        if not re.fullmatch(r"[А-ЯЁ][а-яё]+", v):
            raise ValueError("Должно быть с заглавной буквы, только кириллица, без пробелов")
        return v

    @validator("birth_date")
    def validate_birth_date(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Дата рождения не может быть из будущего")
        return v

    @validator("phone")
    def validate_phone(cls, v: str) -> str:

        v = v.strip().replace(" ", "")
        pattern = re.compile(r"^(\+7|8)\d{10}$")
        if not pattern.fullmatch(v):
            raise ValueError("Телефон должен быть в формате +7XXXXXXXXXX или 8XXXXXXXXXX")
        return v

    @validator("problem_found_at")
    def validate_problem_found_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v

        now_utc = datetime.now(timezone.utc)
        if v.tzinfo is not None:
            v_utc = v.astimezone(timezone.utc)
        else:
            v_utc = v.replace(tzinfo=timezone.utc)

        if v_utc > now_utc:
            raise ValueError("Время обнаружения проблемы не может быть из будущего")
        return v


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def save_request_to_file(data: dict) -> Path:

    timestamp = datetime.now().isoformat(timespec="milliseconds").replace(":", "-")
    filename = DATA_DIR / f"request_{timestamp}.json"
    with filename.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/support")
async def create_support_request(req: SupportRequest):
    data = req.model_dump(mode="json")

    try:
        file_path = save_request_to_file(data)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить файл: {e}")

    return {
        "status": "ok",
        "saved_to": file_path.name,
        "data": data,
    }


# Для локального запуска: python main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
