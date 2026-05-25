"""
API для синхронизации данных с базой
"""
from aiogram import types
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Date, Boolean, Enum, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
from decimal import Decimal
import os
import enum
from typing import Optional, List, Dict

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///records.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Модель БД для записей покупок/продаж
class Record(Base):
    __tablename__ = 'records'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, default=1)
    seller_group = Column(String, index=True)
    custom_seller_name = Column(String, nullable=True)
    device = Column(String)
    quantity = Column(Integer, default=1)
    buy_price = Column(Float, default=0)
    sell_price = Column(Float, default=0)
    buyer_name = Column(String, nullable=True)
    date = Column(Date, index=True, default=date.today)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    is_deleted = Column(Boolean, default=False)

# Типы транзакций кассы
class TransactionType(str, enum.Enum):
    INITIAL = "initial"
    PROFIT = "profit"
    LOSS = "loss"
    OTHER = "other"

# Модель для кассы
class CashTransaction(Base):
    __tablename__ = 'cash_transactions'

    id = Column(Integer, primary_key=True)
    type = Column(String, default=TransactionType.OTHER.value)
    amount = Column(Float)
    description = Column(String, nullable=True)
    date = Column(Date, index=True, default=date.today)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

Base.metadata.create_all(bind=engine)

# ============ ФУНКЦИИ РАБОТЫ С ЗАПИСЯМИ ============

async def save_record(
    user_id: int,
    seller_group: str,
    device: str,
    buy_price: float = 0,
    sell_price: float = 0,
    quantity: int = 1,
    buyer_name: Optional[str] = None,
    custom_seller_name: Optional[str] = None,
    record_date: Optional[date] = None
):
    """Сохранить запись в БД"""
    db = SessionLocal()
    try:
        record = Record(
            user_id=user_id,
            seller_group=seller_group,
            device=device,
            buy_price=buy_price,
            sell_price=sell_price,
            quantity=quantity,
            buyer_name=buyer_name,
            custom_seller_name=custom_seller_name,
            date=record_date or date.today()
        )
        db.add(record)
        db.commit()
        return record
    finally:
        db.close()

async def get_user_records(user_id: int):
    """Получить все записи пользователя"""
    db = SessionLocal()
    try:
        records = db.query(Record).filter(
            Record.user_id == user_id,
            Record.is_deleted == False
        ).order_by(Record.timestamp.desc()).all()
        return records
    finally:
        db.close()

async def get_all_records():
    """Получить все (общие) записи"""
    db = SessionLocal()
    try:
        records = db.query(Record).filter(
            Record.is_deleted == False
        ).order_by(Record.timestamp.desc()).all()
        return records
    finally:
        db.close()

async def delete_record(record_id: int):
    """Мягкое удаление записи"""
    db = SessionLocal()
    try:
        record = db.query(Record).filter(Record.id == record_id).first()
        if record:
            record.is_deleted = True
            db.commit()
        return record
    finally:
        db.close()

# ============ ФУНКЦИИ СТАТИСТИКИ ============

def get_stats(period: str = 'day', start_date: Optional[date] = None, end_date: Optional[date] = None):
    """
    Получить статистику за период.
    period: 'day', 'week', 'month', 'all'
    """
    db = SessionLocal()
    try:
        from datetime import timedelta

        if not start_date:
            if period == 'day':
                start_date = date.today()
                end_date = date.today()
            elif period == 'week':
                today = date.today()
                start_date = today - timedelta(days=today.weekday())
                end_date = today
            elif period == 'month':
                today = date.today()
                start_date = today.replace(day=1)
                end_date = today
            else:  # all
                start_date = None
                end_date = date.today()

        query = db.query(Record).filter(Record.is_deleted == False)

        if start_date:
            query = query.filter(Record.date >= start_date)
        if end_date:
            query = query.filter(Record.date <= end_date)

        records = query.all()

        # Рассчитываем статистику
        total_profit = 0
        total_buys = 0
        total_sells = 0
        by_seller = {}
        by_date = {}

        for record in records:
            profit_per_unit = record.sell_price - record.buy_price
            total_profit += profit_per_unit * record.quantity
            total_buys += record.buy_price * record.quantity
            total_sells += record.sell_price * record.quantity

            seller_name = record.custom_seller_name or record.seller_group

            if seller_name not in by_seller:
                by_seller[seller_name] = {
                    "profit": 0,
                    "deals": 0,
                    "sum_buys": 0,
                    "sum_sells": 0,
                    "quantity": 0
                }

            by_seller[seller_name]["profit"] += profit_per_unit * record.quantity
            by_seller[seller_name]["deals"] += 1
            by_seller[seller_name]["sum_buys"] += record.buy_price * record.quantity
            by_seller[seller_name]["sum_sells"] += record.sell_price * record.quantity
            by_seller[seller_name]["quantity"] += record.quantity

            date_key = record.date.strftime('%Y-%m-%d')
            if date_key not in by_date:
                by_date[date_key] = {"profit": 0, "deals": 0, "buys": 0, "sells": 0}

            by_date[date_key]["profit"] += profit_per_unit * record.quantity
            by_date[date_key]["deals"] += 1
            by_date[date_key]["buys"] += record.buy_price * record.quantity
            by_date[date_key]["sells"] += record.sell_price * record.quantity

        return {
            "total_profit": round(total_profit, 2),
            "total_buys": round(total_buys, 2),
            "total_sells": round(total_sells, 2),
            "deals_count": len(records),
            "total_quantity": sum(r.quantity for r in records),
            "by_seller": by_seller,
            "by_date": by_date,
            "period": period,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        }
    finally:
        db.close()

async def get_seller_history(seller_name: str):
    """Получить всю историю по продавцу"""
    db = SessionLocal()
    try:
        records = db.query(Record).filter(
            Record.is_deleted == False,
            (Record.seller_group == seller_name) | (Record.custom_seller_name == seller_name)
        ).order_by(Record.timestamp.desc()).all()
        return records
    finally:
        db.close()

# ============ ФУНКЦИИ КАССЫ ============

async def initialize_cash(initial_amount: float):
    """Инициализировать кассу"""
    db = SessionLocal()
    try:
        transaction = CashTransaction(
            type=TransactionType.INITIAL.value,
            amount=initial_amount,
            description="Начальный остаток кассы"
        )
        db.add(transaction)
        db.commit()
        return transaction
    finally:
        db.close()

async def add_cash_transaction(amount: float, trans_type: str = TransactionType.OTHER.value, description: str = ""):
    """Добавить транзакцию в кассу"""
    db = SessionLocal()
    try:
        transaction = CashTransaction(
            type=trans_type,
            amount=amount,
            description=description
        )
        db.add(transaction)
        db.commit()
        return transaction
    finally:
        db.close()

def get_cash_balance():
    """Получить текущий баланс кассы"""
    db = SessionLocal()
    try:
        transactions = db.query(CashTransaction).all()
        balance = sum(t.amount for t in transactions)
        return round(balance, 2)
    finally:
        db.close()

async def get_cash_history():
    """Получить историю кассы"""
    db = SessionLocal()
    try:
        transactions = db.query(CashTransaction).order_by(CashTransaction.timestamp.desc()).all()
        return transactions
    finally:
        db.close()
