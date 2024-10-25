from python:3.8-slim-buster

RUN apt-get update && apt-get install -y \
    python3-dev \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install psycopg2-binary
RUN pip install PyTelegramBotAPI
RUN pip install pytz
RUN pip install schedule

COPY . /app
WORKDIR /app

RUN find . -type d -name "__pycache__" -exec rm -rf {} +

CMD ["python3", "src/main.py"]