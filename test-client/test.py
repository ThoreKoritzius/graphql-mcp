import os
from langchain_openai import ChatOpenAI
from mcp_use import MCPClient, MCPAgent
import pandas as pd
import asyncio
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI()

class Question(BaseModel):
    """
    Request model containing a single question string.
    """
    question: str

# Configuration for the MCP remote server
config = {
    "mcpServers": {
        "graphql_mcp": {
            "command": "npx",
            "args": [
                "mcp-remote",
                "http://127.0.0.1:5001/mcp"
            ]
        }
    }
}

# Global agent object to be initialized on app startup
agent: MCPAgent = None

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event handler.
    Initializes the MCPClient and ChatOpenAI-based MCPAgent.
    """
    client = MCPClient.from_dict(config)
    llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=os.getenv("OPENAI_API_KEY"))
    global agent
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

@app.post("/ask")
async def ask_question(q: Question):
    """
    POST endpoint to process a natural language question using the MCPAgent.

    Parameters:
    - q (Question): A Pydantic model containing the user question.

    Returns:
    - JSON response containing the agent's result.
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not ready")
    result = await agent.run(q.question)
    return {"result": result}

# Optional: run with uvicorn if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("test:app", host="0.0.0.0", port=3000, reload=True)
