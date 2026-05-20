import asyncio
import re
import pandas as pd
from telethon import TelegramClient
from telethon.network.connection import ConnectionTcpMTProxyRandomizedIntermediate
import socks

# ========== НАСТРОЙКИ (ЗАМЕНИТЕ НА СВОИ) ==========
API_ID = 39337349
API_HASH = 'd1f27f9ba12a0e4c4d6bda3eb9106903'
# Каналы: словарь {отображаемое_имя: юзернейм}
CHANNELS = {
    'DM': 'dmprlce',   # DM mobile price
    # 'Другой канал': 'username2'
}
OUTPUT_EXCEL = 'prices.xlsx'

# ========== НАСТРОЙКИ ПРОКСИ (SOCKS5 - более стабильно) ==========
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 1080
PROXY_SECRET = 'dd3e3c543a08a89735afc137467e877c80'

proxy = (PROXY_HOST, PROXY_PORT, PROXY_SECRET)

def normalize_price(price_str: str) -> int:
    """Превращает '26,900' или '18.800' или '26 900' в 26900"""
    # Удаляем пробелы, запятые, точки
    cleaned = re.sub(r'[^\d]', '', price_str)
    return int(cleaned) if cleaned else None

# ========== ФУНКЦИЯ ПАРСИНГА ==========
def parse_message(text: str) -> list:
    """
    Возвращает список кортежей (устройство_с_заменой_флагов, цена_int)
    """
    results = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Пропускаем служебные строки, например "От 10шт - 1 100" или "Заказать - @..."
        if re.search(r'от\s+\d+шт', line, re.IGNORECASE) or 'заказать' in line.lower():
            continue

        # Ищем цену в строке
        price = None
        device_part = line

        # Вариант 1: есть дефис
        if '-' in line:
            parts = line.split('-', 1)
            device_part = parts[0].strip()
            price_str = parts[1].strip()
            # Если после дефиса пусто или не число – пропускаем
            if price_str and re.search(r'\d', price_str):
                price_str = re.sub(r'[^\d]', '', price_str)  # оставляем только цифры
                if price_str:
                    price = int(price_str)
        else:
            # Вариант 2: нет дефиса – ищем последнее число в строке (отделено пробелом)
            numbers = re.findall(r'\b(\d[\d\s]*\d)\b', line)  # числа с возможными пробелами внутри
            if numbers:
                # Берём последнее число
                last_num = numbers[-1]
                price_str = re.sub(r'\s', '', last_num)
                if price_str:
                    price = int(price_str)
                    # Всё до последнего числа – название устройства
                    device_part = line[:line.rfind(last_num)].strip()

        if price is None:
            continue  # нет цены – не добавляем

        # Очищаем название устройства: убираем лишние пробелы, заменяем флаги
        device_part = re.sub(r'\s+', ' ', device_part).strip()

        # Замена флагов
        device_part = device_part.replace('🇯🇵', 'eSim')
        device_part = device_part.replace('🇭🇰', '1Sim')
        # Можно добавить замену других флагов при желании:
        # device_part = device_part.replace('🇺🇸', 'USA') и т.д.

        # Убираем одиночные флаги, которые могли остаться (например, в конце строки)
        # но оставляем их в составе названия, если они есть внутри

        # Доп. чистка: убираем лишние дефисы в начале/конце
        device_part = device_part.strip('- ')

        if device_part and price:
            results.append((device_part, price))

    return results

async def fetch_prices_from_channel(client, channel_username):
    """Собирает все цены из последних 500 сообщений канала"""
    prices = []
    try:
        entity = await client.get_entity(channel_username)
        async for message in client.iter_messages(entity, limit=500):
            if message.text:
                parsed = parse_message(message.text)
                prices.extend(parsed)
            await asyncio.sleep(0.3)  # задержка
    except Exception as e:
        print(f"Ошибка при чтении {channel_username}: {e}")
    return prices

async def main():
    client = TelegramClient(
        'session_name', API_ID, API_HASH,
        connection=ConnectionTcpMTProxyRandomizedIntermediate,
        proxy=proxy,
        connection_retries=5,
        retry_delay=3,
        timeout=15
    )
    await client.start()
    print("Подключено. Собираю данные...")

    all_data = {}  # {channel_display_name: [(device, price)]}
    for display_name, username in CHANNELS.items():
        print(f"Читаю канал {display_name} (@{username})...")
        prices = await fetch_prices_from_channel(client, username)
        all_data[display_name] = prices
        print(f"  Найдено {len(prices)} позиций")

    # Строим список уникальных устройств (в порядке первого появления)
    unique_devices = []
    for prices in all_data.values():
        for device, _ in prices:
            if device not in unique_devices:
                unique_devices.append(device)

    # Создаём DataFrame
    df = pd.DataFrame({'Устройство': unique_devices})

    # Для каждого канала добавляем столбец с ценами
    for ch_name, prices in all_data.items():
        price_dict = dict(prices)  # {device: price}
        df[ch_name] = df['Устройство'].map(price_dict)

    # Сохраняем в Excel
    with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Цены', index=False)

    print(f"Готово! Таблица сохранена в {OUTPUT_EXCEL}")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())