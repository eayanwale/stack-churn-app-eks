# ---- STACK IT Customer Churn Predictor ------------------------------------
# Small, production-ish image: gunicorn + Flask, runs as a non-root user.
FROM python:3.12-slim

# Faster, quieter Python; no .pyc; unbuffered logs to CloudWatch/console
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    INFERENCE_MODE=local

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + the bundled model (used when INFERENCE_MODE=local)
COPY app/ ./app/
COPY model/ ./model/
COPY wsgi.py ./

# Run as an unprivileged user
RUN useradd -u 10001 -m appuser
USER 10001

EXPOSE 8080

# Container health check hits the app's /health route
HEALTHCHECK --interval=30s --timeout=4s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,os,sys; \
sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8080')+'/health').status==200 else sys.exit(1)"

# 2 workers is fine for a demo; raise for more traffic
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 60 wsgi:app"]
