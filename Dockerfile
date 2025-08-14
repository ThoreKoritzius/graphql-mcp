# Builder image with caching and chef for dependency optimization
FROM rust:1.85 AS base
RUN cargo install sccache --version ^0.7
RUN cargo install cargo-chef --version ^0.1
ENV RUSTC_WRAPPER=sccache SCCACHE_DIR=/sccache

# Prepare build plan
FROM base AS planner
WORKDIR /app
COPY . .
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=$SCCACHE_DIR,sharing=locked \
    cargo chef prepare --recipe-path recipe.json

# Build dependencies and project
FROM base AS builder
WORKDIR /app
COPY --from=planner /app/recipe.json recipe.json
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=$SCCACHE_DIR,sharing=locked \
    cargo chef cook --release --recipe-path recipe.json
COPY . .
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=$SCCACHE_DIR,sharing=locked \
    cargo build --release

# Final minimal image
FROM debian:bookworm-slim AS runtime
# Install OpenSSL 3 for libssl.so.3 and create appuser in one layer
RUN apt-get update && apt-get install -y libssl3 && rm -rf /var/lib/apt/lists/* && useradd -m appuser
WORKDIR /app
COPY --from=builder /app/target/release/graphql-mcp /app/graphql-mcp
COPY --from=builder /app/.env /app/.env 
# If you use an .env file
ENV RUST_LOG=debug
EXPOSE 5000
USER appuser

CMD /app/graphql-mcp --endpoint "$ENDPOINT"