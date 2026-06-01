FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium

COPY app/ ./app/
COPY worker/ ./worker/
COPY static/ ./static/

ENV PYTHONUNBUFFERED=1
ENV COOKIES_PATH=/data/ig_session.json

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
