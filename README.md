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

This repo contains three services  
`graphql-mcp`: The main graphql mcp server. you can either run it as a docker service (where the code is build), or use `cargo run` with an argument --endpoint http://your-graphql-endpoint to specifically connect to your specific endpoint

`test-graphql-server` a mock graphql server to test the mcp, so mcp redirects to this

`test-llm-server` a test llm server,

you need to specifiy `OPENAI_API_KEY` in a .env  file. Then

```
docker-compose up --build
```

when all services running, you can test the mcp by querying the test-llm-server

```bash
curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "What fields are in the GraphQL table?"}'
```

and see the agent progress in your docker logs.

Alternatively connect via your own llm service, e.g. claude etc via
```json
{
  "mcpServers": {
      "graphql_mcp": {
            "url": "http://graphql-mcp-server:5001/sse"
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
