FROM rust:1.74 AS dev
RUN rustup install nightly && rustup default nightly
WORKDIR /app
COPY . .
RUN useradd -m appuser && chown -R appuser:appuser /app

USER appuser
WORKDIR /app
ENV RUST_LOG=debug
EXPOSE 5000
CMD ["cargo", "run", "--", "--endpoint", "http://test-graphql-server:8000"]
