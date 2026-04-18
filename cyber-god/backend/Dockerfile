# FastAPI + MCP subprocess backend
# PYTHONUNBUFFERED=1 is CRITICAL — prevents MCP stdio subprocess from hanging
# inside Docker due to Python's block buffering in non-TTY mode.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first (layer cache: changes less often than code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
