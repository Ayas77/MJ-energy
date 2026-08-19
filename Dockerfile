FROM python:3.11-slim

WORKDIR /app

# Отключаем буферизацию логов
ENV PYTHONUNBUFFERED=1

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код
COPY . .

CMD ["python", "main.py"]
