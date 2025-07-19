FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install -r requirements.txt

COPY backend backend

CMD python -OOm uvicorn backend.app:app --host 0.0.0.0 --port "${PORT}"
