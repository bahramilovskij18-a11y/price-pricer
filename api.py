"""
FastAPI сервер для синхронизации данных и webhook бота
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import date, datetime
import os
from pathlib import Path
from dotenv import load_dotenv
from database import (
    save_record, get_user_records, get_all_records, delete_record,
    get_stats, get_seller_history, get_cash_balance,
    initialize_cash, add_cash_transaction, get_cash_history,
    TransactionType
)
from bot import dp, bot

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

# Startup event для установки webhook
@app.on_event("startup")
async def setup_webhook():
    """Установить webhook при старте сервера"""
    from bot import WEBHOOK_URL
    try:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url != WEBHOOK_URL:
            await bot.set_webhook(url=WEBHOOK_URL)
            print(f"✅ Webhook установлен: {WEBHOOK_URL}")
    except Exception as e:
        print(f"⚠️ Ошибка при установке webhook: {e}")

# ============ PYDANTIC МОДЕЛИ ============

class RecordCreate(BaseModel):
    user_id: int = 1
    seller_group: str
    device: str
    buy_price: float = 0
    sell_price: float = 0
    quantity: int = 1
    buyer_name: Optional[str] = None
    custom_seller_name: Optional[str] = None

class RecordResponse(BaseModel):
    id: int
    user_id: int
    seller_group: str
    device: str
    buy_price: float
    sell_price: float
    quantity: int
    buyer_name: Optional[str]
    custom_seller_name: Optional[str]
    date: str
    timestamp: str

class CashTransactionCreate(BaseModel):
    amount: float
    trans_type: str = TransactionType.OTHER.value
    description: Optional[str] = None

# ============ ОСНОВНЫЕ API ENDPOINTS ============

@app.get("/health")
async def health():
    """Проверка здоровья сервера"""
    return {"status": "ok"}

@app.post("/webhook/bot")
async def webhook_handler(update: dict):
    """Webhook endpoint для получения обновлений от Telegram"""
    from aiogram.types import Update
    try:
        telegram_update = Update(**update)
        await dp.feed_update(bot, telegram_update)
        return {"ok": True}
    except Exception as e:
        print(f"Error processing update: {e}")
        return {"ok": False}

# ============ ЗАПИСИ API ============

@app.post("/api/records")
async def create_record(record: RecordCreate):
    """Создать новую запись"""
    try:
        saved = await save_record(
            user_id=record.user_id,
            seller_group=record.seller_group,
            device=record.device,
            buy_price=record.buy_price,
            sell_price=record.sell_price,
            quantity=record.quantity,
            buyer_name=record.buyer_name,
            custom_seller_name=record.custom_seller_name
        )
        return {
            "status": "ok",
            "message": "Запись создана",
            "record_id": saved.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/records")
async def get_records(user_id: int = Query(None)):
    """Получить все записи (или записи пользователя если указан user_id)"""
    try:
        if user_id:
            records = await get_user_records(user_id)
        else:
            records = await get_all_records()

        return {
            "status": "ok",
            "records": [
                {
                    "id": r.id,
                    "seller_group": r.seller_group,
                    "custom_seller_name": r.custom_seller_name,
                    "device": r.device,
                    "quantity": r.quantity,
                    "buy_price": r.buy_price,
                    "sell_price": r.sell_price,
                    "profit": (r.sell_price - r.buy_price) * r.quantity,
                    "buyer_name": r.buyer_name,
                    "date": r.date.isoformat(),
                    "timestamp": r.timestamp.isoformat()
                } for r in records
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/records/{record_id}")
async def remove_record(record_id: int):
    """Удалить запись"""
    try:
        await delete_record(record_id)
        return {"status": "ok", "message": "Запись удалена"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============ СТАТИСТИКА API ============

@app.get("/api/stats")
async def get_statistics(
    period: str = Query("day"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Получить статистику.
    period: day, week, month, all
    """
    try:
        start = None
        end = None

        if start_date:
            start = datetime.fromisoformat(start_date).date()
        if end_date:
            end = datetime.fromisoformat(end_date).date()

        stats = get_stats(period=period, start_date=start, end_date=end)
        return {"status": "ok", "data": stats}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/records/seller/{seller_name}")
async def get_seller_records(seller_name: str, period: str = Query("all")):
    """Получить всю историю по продавцу"""
    try:
        records = await get_seller_history(seller_name)

        if period == "today":
            records = [r for r in records if r.date == date.today()]
        elif period == "week":
            from datetime import timedelta
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            records = [r for r in records if r.date >= week_start]
        elif period == "month":
            today = date.today()
            records = [r for r in records if r.date.year == today.year and r.date.month == today.month]

        return {
            "status": "ok",
            "seller": seller_name,
            "records": [
                {
                    "id": r.id,
                    "device": r.device,
                    "quantity": r.quantity,
                    "buy_price": r.buy_price,
                    "sell_price": r.sell_price,
                    "profit": (r.sell_price - r.buy_price) * r.quantity,
                    "buyer_name": r.buyer_name,
                    "date": r.date.isoformat(),
                    "timestamp": r.timestamp.isoformat()
                } for r in records
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============ КАССА API ============

@app.post("/api/cash/initialize")
async def init_cash(amount: float):
    """Инициализировать кассу"""
    try:
        await initialize_cash(amount)
        return {
            "status": "ok",
            "message": "Касса инициализирована",
            "balance": get_cash_balance()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/cash/transaction")
async def add_transaction(transaction: CashTransactionCreate):
    """Добавить транзакцию"""
    try:
        await add_cash_transaction(
            amount=transaction.amount,
            trans_type=transaction.trans_type,
            description=transaction.description or ""
        )
        return {
            "status": "ok",
            "message": "Транзакция добавлена",
            "balance": get_cash_balance()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/cash/balance")
async def get_balance():
    """Получить текущий баланс кассы"""
    try:
        balance = get_cash_balance()
        return {
            "status": "ok",
            "balance": balance
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/cash/history")
async def get_cash_trans_history():
    """Получить историю кассы"""
    try:
        transactions = await get_cash_history()
        return {
            "status": "ok",
            "transactions": [
                {
                    "id": t.id,
                    "type": t.type,
                    "amount": t.amount,
                    "description": t.description,
                    "date": t.date.isoformat(),
                    "timestamp": t.timestamp.isoformat()
                } for t in transactions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============ СТАТИЧЕСКИЕ ФАЙЛЫ ============

STATIC_DIR = Path(__file__).parent

@app.get("/")
async def root():
    """Главная страница"""
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/index.html")
async def index():
    """Открыть приложение"""
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/", StaticFiles(directory=STATIC_DIR, html=False), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
