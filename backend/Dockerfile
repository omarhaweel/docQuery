# DocQuery backend API
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt fastapi uvicorn
COPY backend ./backend
COPY run_api.py ./

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.interface:app --host 0.0.0.0 --port ${PORT:-8000}"]
