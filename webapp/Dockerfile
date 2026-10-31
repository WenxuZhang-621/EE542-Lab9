FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1
WORKDIR /app
COPY requirements-a.txt ./
COPY rag/requirements.txt rag/requirements.txt
COPY webapp/backend/requirements.txt webapp/backend/requirements.txt
RUN pip install --no-cache-dir -r requirements-a.txt
COPY shared/ shared/
COPY config/ config/
COPY rag/ rag/
COPY data/topic/ data/topic/
COPY webapp/ webapp/
COPY scripts/ scripts/
RUN useradd --create-home --uid 10001 labuser
USER labuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "webapp.backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
