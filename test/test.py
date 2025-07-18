from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPClient, MCPAgent
import pandas as pd
import asyncio
import subprocess

config = {
    "mcpServers": {
        "graphql_mcp": {
            "url": "http://localhost:5001/sse"
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
    
    while True:
        # Read user input; exit interactive loop if the user types "exit" or "quit"
        user_input = input("\nEnter your question (or type 'exit' to quit): ")
        if user_input.lower() in ('exit', 'quit'):
            print("Exiting interactive CLI.")
            break
        
        result = await agent.run(user_input)
        print(f"\nResult: {result}")

if __name__ == "__main__":
    asyncio.run(main())
