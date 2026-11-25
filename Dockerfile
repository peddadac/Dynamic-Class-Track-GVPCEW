
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

COPY requirements.txt .
RUN pip install -v --no-cache-dir --default-timeout=300 --retries=10 -r requirements.txt
COPY . .

EXPOSE 5000

CMD ["python", "run.py"]
