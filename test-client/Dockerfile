# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install any system dependencies (if needed)
RUN apt-get update && apt-get install -y gcc

# Copy dependency file and install Python dependencies
# Make sure you have a requirements.txt file listing:
# dotenv, langchain_openai, mcp_use, pandas, asyncio (if not built-in), and any other needed packages.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the project files into the container at /app
COPY . .

CMD ["uvicorn", "test:app", "--host", "0.0.0.0", "--port", "3000"]