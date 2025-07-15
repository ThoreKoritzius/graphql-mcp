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

The server will be running at: [http://localhost:5000](http://localhost:5000)

## Usage

A simple test script is provided by calling `python3 test/test.py`, where you can test the interaction with the MCP Server via OpenAI. For this work, you need to set your `OPENAI_API_KEY` in `test/.env`.

Connect to Claude or other LLMs via the following config
```json
{
  "mcpServers": {
      "graphql_mcp": {
         "command": "target/release/graphql-mcp",
         "args": []
      }
   }
}
```
### Running the Server

To start the server normally without inspection use

```bash
cargo run -- --endpoint http://127.0.0.1:8000
```

with your graphql server endpoint.

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
