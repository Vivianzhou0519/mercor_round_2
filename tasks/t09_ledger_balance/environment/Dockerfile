FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.3.4

WORKDIR /app

COPY ledger.py /app/ledger.py

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
