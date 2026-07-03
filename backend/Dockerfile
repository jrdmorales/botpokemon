FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e . 2>/dev/null || true
COPY . .
RUN pip install --no-cache-dir -e .

# Entrypoint se define en docker-compose según el servicio:
#   api:    uvicorn app.api.main:app --host 0.0.0.0 --port 8000
#   worker: python -m app.worker
#   bot:    python -m app.telegram.bot
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
