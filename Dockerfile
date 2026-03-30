FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY static/ static/

RUN pip install --no-cache-dir .

ENV DOCEXTRACT_STATIC_DIR=/app/static

EXPOSE 8000

CMD ["uvicorn", "docextract.app:app", "--host", "0.0.0.0", "--port", "8000"]
