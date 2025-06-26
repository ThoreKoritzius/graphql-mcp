# GraphQL MCP Server

Welcome to the GraphQL MCP Server repository. This experimental project is designed to help you connect an MCP Server with GraphQL using Rust.

## Overview

This project provides a lightweight GraphQL server implemented in Rust. It serves as a tool for learning, experimentation, and prototyping with GraphQL queries and Rust’s performance and safety features.

## Prerequisites

- Rust and Cargo (install via https://rustup.rs)
- (Optional) Docker for containerized deployments

## Getting Started

1. Clone the repository:
   `git clone https://github.com/ThoreKoritzius/graphql-mcp.git`
2. Navigate into the project directory:
   `cd graphql-mcp`
3. Run the server:
   `cargo run`

## Usage

The server will be running at: [http://localhost:5000](http://localhost:5000)

### Running the Server

To start the server normally without inspection:

```bash
cargo run
```

This will start the application and serve it at `http://localhost:5000`.

### Inspecting with Inspector (Optional)

To inspect the server behavior checkout and install [https://github.com/modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector), use the following command instead:

```bash
npx @modelcontextprotocol/inspector cargo run
```

Select the **Transport Type**: `STDIO`.

This will launch the server with Inspector attached for live introspection.


## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests with improvements.
