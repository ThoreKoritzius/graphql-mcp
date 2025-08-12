

# Stage 1: Build with Poetry

# Stage 1: Build with Poetry and bundle venv

# Stage 1: Build with Poetry and bundle venv
FROM python:3.12-slim AS builder
RUN pip install --no-cache-dir "poetry>=1.2.0" "poetry-plugin-bundle>=0.2.0"
WORKDIR /src
COPY . .
RUN poetry bundle venv --python=/usr/local/bin/python --only=main /venv

# Stage 2: Minimal runtime
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /venv /venv
COPY test_graphql_server/ ./test_graphql_server/
EXPOSE 8000
ENTRYPOINT ["/venv/bin/uvicorn", "test_graphql_server:app", "--host", "0.0.0.0", "--port", "8000"]
