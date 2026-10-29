FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.3.4

WORKDIR /app

COPY slug.py /app/slug.py

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
