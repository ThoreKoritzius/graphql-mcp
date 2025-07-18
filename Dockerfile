FROM rust:1.74 AS builder
RUN rustup install nightly && rustup default nightly
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim AS runtime
RUN apt-get update \
 && apt-get install -y --no-install-recommends libssl3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser
COPY --from=builder /app/target/release/graphql-mcp /usr/local/bin/server
RUN chown appuser:appuser /usr/local/bin/server

USER appuser
WORKDIR /home/appuser
ENV RUST_LOG=debug
EXPOSE 5000
CMD ["server", "--endpoint", "http://test-graphql-server:8000"]

