"""
FastAPI сервер для синхронизации данных
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import os
from pathlib import Path
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

# Папка с статическими файлами
STATIC_DIR = Path(__file__).parent

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=False), name="static")

# Маршрут для главной страницы
@app.get("/")
async def root():
    """Главная страница"""
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/index.html")
async def index():
    """Открыть приложение"""
    return FileResponse(STATIC_DIR / "index.html")

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
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
