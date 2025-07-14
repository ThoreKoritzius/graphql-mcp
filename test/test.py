from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPClient, MCPAgent
import pandas as pd
import asyncio
import subprocess

config = {
    "mcpServers": {
        "rust_mcp": {
            "command": "target/release/graphql-mcp",
             "args": []
        }
    }
}

def run_cargo_build():
    """
    Runs 'cargo build --release' and prints the build output.
    Raises an exception if the build fails.
    """
    print("Building MCP server (cargo build --release)...")
    try:
        result = subprocess.run(
            ["cargo", "build", "--release"],
            check=True,
            capture_output=True,
            text=True
        )
        print("Cargo build completed successfully.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Cargo build failed:")
        print(e.stderr)
        raise

async def main():
    load_dotenv()
    
    try:
        run_cargo_build()
    except Exception:
        return

    client = MCPClient.from_dict(config)
    llm = ChatOpenAI(model="gpt-4o-mini")
    agent = MCPAgent(llm=llm, client=client, max_steps=30)
    result = await agent.run(
        "What planets in the galaxy? tell me the type in grapqhl",
    )
    print(f"\nResult: {result}")

if __name__ == "__main__":
    asyncio.run(main())
