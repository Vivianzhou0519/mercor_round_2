FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.3.4

WORKDIR /app

COPY iso4217.py /app/iso4217.py
COPY money.py /app/money.py

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
