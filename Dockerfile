FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY .env /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app"]