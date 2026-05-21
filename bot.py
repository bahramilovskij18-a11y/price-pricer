import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.command import Command
from aiogram.fsm.storage.memory import MemoryStorage
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из текущей папки
load_dotenv(Path(__file__).parent / '.env')

TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://price-pricer.onrender.com/index.html')

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    """Стартовая команда с кнопкой открытия приложения"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='📊 Открыть приложение',
            web_app=WebAppInfo(url=WEB_APP_URL)
        )]
    ])

    await message.answer(
        '👋 Добро пожаловать в приложение учета устройств!\n\n'
        'Нажмите кнопку ниже, чтобы открыть приложение.',
        reply_markup=keyboard
    )

@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    """Справка"""
    await message.answer(
        '📚 Справка по приложению:\n\n'
        '1️⃣ Выберите группу покупки\n'
        '2️⃣ Введите название устройства\n'
        '3️⃣ Добавьте цену покупки и/или продажи\n'
        '4️⃣ Нажмите "Добавить запись"\n\n'
        'История сохраняется автоматически.'
    )

async def main():
    """Запуск бота"""
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
