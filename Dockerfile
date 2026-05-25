FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Запуск API с webhook для бота
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
