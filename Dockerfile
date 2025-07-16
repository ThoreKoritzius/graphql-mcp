# Build stage
FROM rust:1.74 AS builder

RUN rustup install nightly && rustup default nightly

# Create app directory
WORKDIR /app

# Copy all files
COPY . .

# Build in release mode
RUN cargo build --release

# Runtime stage
FROM debian:bullseye-slim

# Create non-root user (optional but recommended)
RUN useradd -m appuser

# Copy binary from builder
COPY --from=builder /app/target/release/graphql-mcp /usr/local/bin/server

# Set permissions
RUN chown appuser:appuser /usr/local/bin/server

# Use non-root user
USER appuser

# Set working directory
WORKDIR /home/appuser

# Default endpoint (override with `-e` if needed)
ENV RUST_LOG=debug

# Expose port if relevant
EXPOSE 5000

# Run the server
CMD ["server"]
