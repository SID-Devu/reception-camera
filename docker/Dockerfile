FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY .env.example ./

CMD ["python", "src/main.py"]