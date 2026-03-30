FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY static/ static/

RUN pip install --no-cache-dir .

# Persistent data directory for SQLite (mount a volume here in production)
RUN mkdir -p /data
VOLUME /data

EXPOSE 8000

CMD ["uvicorn", "src.docextract.app:app", "--host", "0.0.0.0", "--port", "8000"]
