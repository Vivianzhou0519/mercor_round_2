FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.3.4

WORKDIR /app

COPY invoice.py /app/invoice.py

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
