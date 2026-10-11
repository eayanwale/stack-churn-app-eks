"""Gunicorn entrypoint:  gunicorn --bind 0.0.0.0:8080 wsgi:app"""
from app.main import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
