FROM python:3.11-slim

WORKDIR /app
RUN useradd --create-home appuser
COPY app.py .
USER appuser
CMD ["python", "app.py"]
