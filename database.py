"""
API для синхронизации данных с базой
"""
from aiogram import types
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Подключение к БД
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///records.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Модель БД
class Record(Base):
    __tablename__ = 'records'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    group = Column(String)
    device = Column(String)
    buy_price = Column(Float, default=0)
    sell_price = Column(Float, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Создаем таблицы
Base.metadata.create_all(bind=engine)

async def save_record(user_id: int, group: str, device: str, buy_price: float, sell_price: float):
    """Сохранить запись в БД"""
    db = SessionLocal()
    record = Record(
        user_id=user_id,
        group=group,
        device=device,
        buy_price=buy_price,
        sell_price=sell_price
    )
    db.add(record)
    db.commit()
    db.close()

async def get_user_records(user_id: int):
    """Получить все записи пользователя"""
    db = SessionLocal()
    records = db.query(Record).filter(Record.user_id == user_id).all()
    db.close()
    return records
