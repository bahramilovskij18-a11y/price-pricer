"""
FastAPI сервер для синхронизации данных
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from database import save_record, get_user_records

load_dotenv()

app = FastAPI(title="Price Pricer API")

# CORS для веб-приложения
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы
app.mount("/static", StaticFiles(directory=".", html=True), name="static")

class RecordCreate(BaseModel):
    user_id: int
    group: str
    device: str
    buy_price: float = 0
    sell_price: float = 0

class RecordResponse(BaseModel):
    id: int
    user_id: int
    group: str
    device: str
    buy_price: float
    sell_price: float
    timestamp: str

@app.post("/api/records")
async def create_record(record: RecordCreate):
    """Создать новую запись"""
    try:
        await save_record(
            record.user_id,
            record.group,
            record.device,
            record.buy_price,
            record.sell_price
        )
        return {"status": "ok", "message": "Запись создана"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/records/{user_id}")
async def get_records(user_id: int):
    """Получить записи пользователя"""
    records = await get_user_records(user_id)
    return {"records": records}

@app.get("/health")
async def health():
    """Проверка здоровья сервера"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
