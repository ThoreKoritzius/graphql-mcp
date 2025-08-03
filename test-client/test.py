import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from langchain_openai import ChatOpenAI
from mcp_use import MCPClient, MCPAgent

from fastapi.responses import StreamingResponse
import json
from starlette.responses import Response
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import json


# Initialize FastAPI app
app = FastAPI()

# Pydantic request/response models
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class FullQuestion(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = []

# MCP config
config = {
    "mcpServers": {
        "graphql_mcp": {
            "url": "http://graphql-mcp-server:5001/sse"
        }
    }
}

# Global MCPAgent
agent: MCPAgent = None

@app.on_event("startup")
async def startup_event():
    """
    On startup, initialize MCP client and agent.
    """
    global agent
    client = MCPClient.from_dict(config)
    llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=os.getenv("OPENAI_API_KEY"))
    agent = MCPAgent(llm=llm, client=client, max_steps=30, verbose=True)

# frontend
@app.get("/main.js")
async def main_js():
    return FileResponse("frontend/main.js", media_type="application/javascript")

@app.get("/styles.css")
async def style_css():
    return FileResponse("frontend/styles.css", media_type="text/css")

@app.get("/")
async def serve_index():
    return FileResponse("frontend/index.html")

# main chat endpoint
@app.post("/ask")
async def ask(request: Request):
    params = dict(request.query_params)
    stream = params.get("stream", "false").lower() == "true"
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    question = data.get("question")
    history = data.get("history", [])


    if stream:
        async def event_generator():
            async for step in agent.stream(
                question,
                max_steps=None,
                manage_connector=True,
                external_history=history,
                track_execution=True,
            ):
                print("Yielding:", step, flush=True)
                if isinstance(step, tuple):  # (AgentAction, str)
                    action, observation = step
                    yield (
                        "data: "
                        + json.dumps({
                            "type": "tool_call",
                            "tool": getattr(action, 'tool', None),
                            "tool_input": getattr(action, 'tool_input', None),
                            "observation": observation
                        })
                        + "\n\n"
                    )
                else:
                    yield (
                        "data: "
                        + json.dumps({
                            "type": "result",
                            "result": step
                        })
                        + "\n\n"
                    )
            yield "event: end\ndata: {}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    # Non-stream fallback: single result
    tool_calls = []
    final_result = None
    async for step in agent.stream(
        question,
        max_steps=None,
        manage_connector=True,
        external_history=history,
        track_execution=True,
    ):
        if isinstance(step, tuple):  # (AgentAction, str)
            action, observation = step
            tool_calls.append({
                "tool": getattr(action, 'tool', None),
                "tool_input": getattr(action, 'tool_input', None),
                "observation": observation
            })
        else:
            # The final result (answer string)
            final_result = step

    return JSONResponse({
        "result": final_result,
        "tool_calls": tool_calls
    })
# Optional CLI entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
