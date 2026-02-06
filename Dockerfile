FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get purge -y gcc && \
    apt-get autoremove -y && \
    apt-get install -y libpq5 && \
    rm -rf /var/lib/apt/lists/*

COPY app ./app
COPY tests ./app
COPY create_invite.py /app/

EXPOSE 8000

CMD ["python", "-m", "app.main"]