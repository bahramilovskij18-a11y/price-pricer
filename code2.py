import asyncio
import re
import pandas as pd
import random
from telethon import TelegramClient
from telethon.network.connection import ConnectionTcpMTProxyRandomizedIntermediate
import socks

# ========== НАСТРОЙКИ (ЗАМЕНИТЕ НА СВОИ) ==========
API_ID = 39337349
API_HASH = 'd1f27f9ba12a0e4c4d6bda3eb9106903'
# Каналы: словарь {отображаемое_имя: юзернейм}
CHANNELS = {
    'DM': 'dmprlce',   # DM mobile price
    'Global Market Channel': 'globalmarket_opt',
    'TechDeals | Гаджеты и электроника': 'TechDeals_Official1',
    'Влад Конвент +': '@vlad_konvent',
    #'ПРАЙС': 'dmprlce'
    
}
OUTPUT_EXCEL = 'prices.xlsx'

# ========== НАСТРОЙКИ ПРОКСИ (SOCKS5) ==========
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 1080
PROXY_SECRET = 'dd3e3c543a08a89735afc137467e877c80'

proxy = (PROXY_HOST, PROXY_PORT, PROXY_SECRET)

# ========== ФУНКЦИЯ ПАРСИНГА (УЛУЧШЕННАЯ) ==========
def normalize_price(price_str: str) -> int:
    """Превращает '26,900' или '18.800' или '26 900' в 26900 с валидацией"""
    # Удаляем пробелы, запятые, точки
    cleaned = re.sub(r'[^\d]', '', price_str)
    if not cleaned:
        return None

    price = int(cleaned)
    # Валидация диапазона: 5000 - 200000 рублей
    if 5000 <= price <= 200000:
        return price
    return None

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

        # Пропускаем служебные строки
        if re.search(r'заказать|📱|Apple Watch:|iPad:|MacBook:|ДМ|DM', line, re.IGNORECASE):
            continue
        # Пропускаем строки с условиями типа "От 10шт"
        if re.search(r'от\s+\d+шт', line, re.IGNORECASE):
            continue

        price = None
        device_part = line

        # --- ВАРИАНТ 1: есть дефис ---
        if '-' in line:
            parts = line.split('-', 1)
            left = parts[0].strip()
            right = parts[1].strip()
            # Если справа есть хоть одна цифра – пробуем извлечь цену
            if right and re.search(r'\d', right):
                price = normalize_price(right)
                if price is not None:
                    device_part = left
        else:
            # --- ВАРИАНТ 2: нет дефиса – ищем последнее число в строке ---
            # Ищем все группы цифр, разделители могут быть запятыми, точками, пробелами
            # Но нам нужно именно число, которое может содержать внутри , или .
            # Проще: найти все последовательности цифр, запятых и точек,
            # которые начинаются и заканчиваются цифрой, и взять последнюю.
            candidates = re.findall(r'\b[\d][\d\s,\.]*[\d]\b', line)
            if candidates:
                last_candidate = candidates[-1]
                price = normalize_price(last_candidate)
                if price is not None:
                    # Название устройства – всё, что до последнего кандидата
                    idx = line.rfind(last_candidate)
                    device_part = line[:idx].strip()

        if price is None:
            continue  # не нашли цену – пропускаем

        # Очищаем название устройства
        device_part = re.sub(r'\s+', ' ', device_part).strip()

        # Заменяем флаги
        device_part = device_part.replace('🇯🇵', 'eSim')
        device_part = device_part.replace('🇭🇰', '1Sim')
        # При необходимости можно добавить другие:
        # device_part = device_part.replace('🇺🇸', 'USA')
        # device_part = device_part.replace('🇷🇺', 'RUS')

        # Удаляем лишние дефисы в начале/конце (могут остаться после обрезки)
        device_part = device_part.strip('- ')

        if device_part and price:
            results.append((device_part, price))

    return results

async def fetch_prices_from_channel(client, channel_username):
    """Собирает все цены из последних 500 сообщений канала"""
    prices = []
    try:
        entity = await client.get_entity(channel_username)
        async for message in client.iter_messages(entity, limit=7):
            if message.text:
                parsed = parse_message(message.text)
                prices.extend(parsed)
            await asyncio.sleep(random.uniform(0.5, 1.5))  # задержка 0.5-1.5 сек
        await asyncio.sleep(random.uniform(1, 2))  # задержка между каналами
    except Exception as e:
        print(f"Ошибка при чтении {channel_username}: {e}")
    return prices

async def update_prices(client, last_message_id):
    """Обновляет прайс из всех каналов и отправляет в Telegram"""
    all_data = {}  # {channel_display_name: [(device, price)]}
    for display_name, username in CHANNELS.items():
        try:
            prices = await fetch_prices_from_channel(client, username)
            all_data[display_name] = prices
            print(f"[{display_name}] Найдено {len(prices)} позиций")
        except Exception as e:
            print(f"Ошибка при обновлении {display_name}: {e}")
            all_data[display_name] = []

    # Строим список уникальных устройств в порядке первого появления
    unique_devices = []
    for prices in all_data.values():
        for device, _ in prices:
            if device not in unique_devices:
                unique_devices.append(device)

    # Создаём DataFrame
    df = pd.DataFrame({'Устройство': unique_devices})

    # Для каждого канала добавляем столбец с ценами (последняя цена при повторах)
    for ch_name, prices in all_data.items():
        price_dict = dict(prices)
        df[ch_name] = df['Устройство'].map(price_dict)

    # Сохраняем в Excel с обработкой ошибок
    try:
        with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Цены', index=False)
        print(f"✓ Таблица обновлена в {OUTPUT_EXCEL}")
    except PermissionError:
        print(f"⚠ Ошибка: {OUTPUT_EXCEL} открыт в Excel. Закройте файл.")
        return last_message_id
    except Exception as e:
        print(f"⚠ Ошибка при сохранении: {e}")
        return last_message_id

    # Отправляем/обновляем файл в Saved Messages
    try:
        me = await client.get_entity('me')

        # Удаляем старое сообщение если есть
        if last_message_id:
            try:
                await client.delete_messages(me, last_message_id)
            except:
                pass

        # Отправляем новый файл в избранное
        message = await client.send_file(me, OUTPUT_EXCEL, caption="📊 Актуальные цены")
        print(f"✓ Файл отправлен в Saved Messages (ID: {message.id})")
        return message.id
    except Exception as e:
        print(f"⚠ Ошибка при отправке в Telegram: {e}")
        return last_message_id

async def main():
    client = TelegramClient(
        'session_name', API_ID, API_HASH,
        connection=ConnectionTcpMTProxyRandomizedIntermediate,
        proxy=proxy,
        device_model='iPhone 14',  # выглядит как мобильное приложение
        system_version='16.0',
        connection_retries=5,
        retry_delay=3,
        timeout=15
    )
    await client.start()
    print("✓ Подключено к Telegram\n")

    iteration = 0
    last_message_id = None

    while True:
        iteration += 1
        print(f"\n--- Итерация {iteration} ---")
        last_message_id = await update_prices(client, last_message_id)

        # Случайный интервал 9-11 минут (вместо чётких 10)
        delay = 540 + random.randint(0, 120)  # 9-11 минут
        minutes = delay / 60
        print(f"Следующее обновление через {minutes:.1f} минут...")
        await asyncio.sleep(delay)

if __name__ == '__main__':
    asyncio.run(main())