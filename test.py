from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient
# MCP server config
from langchain_openai import ChatOpenAI
from mcp_use import MCPClient, MCPAgent
import pandas as pd
import asyncio

config = {
    "mcpServers": {
        "rust_mcp": {
            "command": "target/release/graphql-mcp",
             "args": []
        }
    }
}


async def main():
    client = MCPClient.from_dict(config)
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=key)
    agent = MCPAgent(llm=llm, client=client, max_steps=30)
    result = await agent.run(
        "Find the best restaurant in San Francisco",
    )
    print(f"\nResult: {result}")


if __name__ == "__main__":
    asyncio.run(main())