import pandas as pd
import requests
import time
import json
import os
from datetime import datetime

# --- Configuration ---
LLM_MODEL_NAME = "gpt-4.1"

# --- Ensure results directory exists ---
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# --- Generate timestamped filename (this file will be updated incrementally) ---
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_filename = f"{RESULTS_DIR}/result_{timestamp}.csv"

# Load dataset
data = pd.read_csv("dataset.csv")

# --- Pre-create columns with default values to later update in-place ---
data["model_response"] = ""
data["latency_seconds"] = 0.0
data["tool_calls"] = ""
data["num_tool_calls"] = 0
data["status_code"] = 0
data["total_input_tokens"] = 0
data["total_output_tokens"] = 0
data["llm_model_name"] = ""

# Save an initial version so that the file exists
data.to_csv(output_filename, index=False)

# Process each row, update intermediate progress and re-save the file
for i, item in data.iterrows():
    question = item["question"]
    print(f"({i+1}/{len(data)}) Asking: {question}")

    payload = {
        "question": question,
        "stream": False,
        "llm": LLM_MODEL_NAME
    }
    try:
        t0 = time.time()
        resp = requests.post(
            "http://localhost:3000/ask",
            json=payload,
            timeout=500
        )
        t1 = time.time()
        status_code = resp.status_code
        resp.raise_for_status()
        answer_json = resp.json()
        answer = answer_json.get("result")
        total_input_tokens  = answer_json.get("total_input_tokens")
        total_output_tokens = answer_json.get("total_output_tokens")
        tool_calls = answer_json.get("tool_calls", [])
    except Exception as e:
        t1 = time.time()
        status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        answer = f"ERROR: {str(e)}"
        tool_calls = []
        total_input_tokens  = -1
        total_output_tokens = -1

    latency = t1 - t0

    # Update the row with results
    data.at[i, "model_response"] = answer
    data.at[i, "latency_seconds"] = latency
    data.at[i, "tool_calls"] = json.dumps(tool_calls, ensure_ascii=False)
    data.at[i, "num_tool_calls"] = len(tool_calls) if isinstance(tool_calls, list) else 0
    data.at[i, "status_code"] = status_code
    data.at[i, "total_input_tokens"] = total_input_tokens
    data.at[i, "total_output_tokens"] = total_output_tokens
    data.at[i, "llm_model_name"] = LLM_MODEL_NAME

    # Save intermediate progress to the same file after processing each row
    data.to_csv(output_filename, index=False)

print(f"Done. Results saved (and updated incrementally) to {output_filename}.")