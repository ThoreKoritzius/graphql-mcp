# Use official Python runtime as parent image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (in one RUN to maximize cache)
RUN apt-get update && apt-get install -y gcc --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies first to leverage Docker cache
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application source code
COPY . .

CMD ["uvicorn", "test:app", "--host", "0.0.0.0", "--port", "3000"]