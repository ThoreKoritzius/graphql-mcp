import os
import json
from typing import List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback
from langchain.globals import set_llm_cache
from pydantic import BaseModel

from mcp_use import MCPClient, MCPAgent

# ---------------------------------------------------------------------
# Environment & Global Config
# ---------------------------------------------------------------------
load_dotenv()
set_llm_cache(None)

app = FastAPI()
LLM_MODEL_NAME = "gpt-4.1"

# ---------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------
class ChatMessage(BaseModel):
    """Represents a single chat message in the conversation."""
    role: Literal["user", "assistant"]
    content: str


class FullQuestion(BaseModel):
    """Schema for incoming chat requests with optional history."""
    question: str
    history: Optional[List[ChatMessage]] = []


# ---------------------------------------------------------------------
# MCP Configuration
# ---------------------------------------------------------------------
MCP_CONFIG = {
    "mcpServers": {
        "graphql_mcp": {"url": "http://graphql-mcp-server:5001/sse"}
    }
}


@app.on_event("startup")
async def startup_event():
    """Initialize MCP client, LLM, and agent on app startup."""
    global client, llm, agent
    client = MCPClient.from_dict(MCP_CONFIG)
    llm = ChatOpenAI(
        model=LLM_MODEL_NAME,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        cache=False
    )
    agent = MCPAgent(llm=llm, client=client, max_steps=30, verbose=True)


# ---------------------------------------------------------------------
# Frontend Routes
# ---------------------------------------------------------------------
@app.get("/main.js")
async def serve_main_js():
    """Serve frontend JavaScript file."""
    return FileResponse("test_client/frontend/main.js", media_type="application/javascript")


@app.get("/styles.css")
async def serve_styles_css():
    """Serve frontend CSS file."""
    return FileResponse("test_client/frontend/styles.css", media_type="text/css")


@app.get("/")
async def serve_index():
    """Serve main frontend HTML file."""
    return FileResponse("test_client/frontend/index.html")


# ---------------------------------------------------------------------
# Chat Endpoint
# ---------------------------------------------------------------------
@app.post("/ask")
async def ask(request: Request):
    """
    Handle user chat requests with optional streaming.

    Query Parameters:
        stream (bool): Whether to stream responses as SSE.

    Request Body:
        question (str): The user question.
        history (List[ChatMessage], optional): Chat history.

    Returns:
        JSONResponse or StreamingResponse: Depending on `stream` flag.
    """
    params = dict(request.query_params)
    stream = params.get("stream", "false").lower() == "true"

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    question = data.get("question")
    history = data.get("history", [])

    with get_openai_callback() as cb:
        request_llm = ChatOpenAI(
            model=LLM_MODEL_NAME,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            cache=False,
            streaming=True,
            stream_usage=True,
        )

        try:
            request_agent = MCPAgent(
                llm=request_llm,
                client=client,
                max_steps=30,
                verbose=True,
                stream_runnable=False,
            )
        except TypeError:
            request_agent = MCPAgent(
                llm=request_llm,
                client=client,
                max_steps=30,
                verbose=True,
            )

        # -------------------- Streaming Path --------------------
        if stream:
            async def event_generator():
                """Yield Server-Sent Events (SSE) for streaming responses."""
                async for step in request_agent.stream(
                    question,
                    max_steps=None,
                    manage_connector=True,
                    external_history=history,
                    track_execution=True,
                ):
                    if isinstance(step, tuple):
                        action, observation = step
                        yield "data: " + json.dumps({
                            "type": "tool_call",
                            "tool": getattr(action, 'tool', None),
                            "tool_input": getattr(action, 'tool_input', None),
                            "observation": observation,
                            "llm_model_name": LLM_MODEL_NAME
                        }) + "\n\n"
                    else:
                        yield "data: " + json.dumps({
                            "type": "result",
                            "result": step
                        }) + "\n\n"

                # Emit usage metadata at the end of the stream
                usage_payload = {
                    "total_tokens": getattr(cb, "total_tokens", None),
                    "prompt_tokens": getattr(cb, "prompt_tokens", None),
                    "completion_tokens": getattr(cb, "completion_tokens", None),
                    "total_cost": getattr(cb, "total_cost", None),
                }

                yield "data: " + json.dumps({
                    "type": "usage",
                    "usage_metadata": usage_payload
                }) + "\n\n"

                yield "event: end\ndata: {}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        # -------------------- Non-Streaming Path --------------------
        tool_calls = []
        final_result = None
        async for step in request_agent.stream(
            question,
            max_steps=None,
            manage_connector=True,
            external_history=history,
            track_execution=True,
        ):
            if isinstance(step, tuple):
                action, observation = step
                tool_calls.append({
                    "type": "tool_call",
                    "tool": getattr(action, 'tool', None),
                    "tool_input": getattr(action, 'tool_input', None),
                    "observation": observation,
                    "llm_model_name": LLM_MODEL_NAME
                })
            else:
                final_result = step

        usage_payload = {
            "total_tokens": getattr(cb, "total_tokens", None),
            "prompt_tokens": getattr(cb, "prompt_tokens", None),
            "completion_tokens": getattr(cb, "completion_tokens", None),
            "total_cost": getattr(cb, "total_cost", None),
        }

    # Debug log (can be removed in production)
    print("USAGE metadata (non-stream):", usage_payload, flush=True)

    return JSONResponse({
        "result": final_result,
        "tool_calls": tool_calls,
        "usage_metadata": usage_payload
    })


# ---------------------------------------------------------------------
# Optional CLI Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
