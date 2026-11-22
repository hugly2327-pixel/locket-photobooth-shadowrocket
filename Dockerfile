FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    LOCKET_DATA_DIR=/mnt/locket-data \
    UPLOAD_TMP_DIR=/tmp/locket-uploads

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY static ./static

RUN mkdir -p /mnt/locket-data /tmp/locket-uploads \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app /tmp/locket-uploads

USER appuser
EXPOSE 8080
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 300"]
