FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запуск бота и API одновременно
CMD ["sh", "-c", "python bot.py & python api.py"]
