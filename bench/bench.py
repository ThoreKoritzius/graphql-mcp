"""
Benchmarking of the GraphQL MCP Server
"""

import pandas as pd
import requests
import time
import json

# Load dataset
data = pd.read_csv("dataset.csv")

responses = []
latencies = []
tool_calls_list = []
num_tool_calls_list = []
status_codes = []
total_input_tokens_list = []
total_output_tokens_list = []

for i, item in data.iterrows():
    question = item["question"]
    print(f"({i+1}/{len(data)}) Asking: {question}")

    payload = {"question": question, "stream": False}
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
    responses.append(answer)
    latencies.append(t1 - t0)
    tool_calls_list.append(json.dumps(tool_calls, ensure_ascii=False))
    num_tool_calls_list.append(len(tool_calls) if isinstance(tool_calls, list) else 0)
    status_codes.append(status_code)
    total_input_tokens_list.append(total_input_tokens)
    total_output_tokens_list.append(total_output_tokens)

# Add new columns to the original DataFrame
data["model_response"] = responses
data["latency_seconds"] = latencies
data["tool_calls"] = tool_calls_list
data["num_tool_calls"] = num_tool_calls_list
data["status_code"] = status_codes
data["total_input_tokens"] = total_input_tokens_list
data["total_output_tokens"] = total_output_tokens_list

# Save as CSV
data.to_csv("dataset_with_model_responses.csv", index=False)
print("Done. Results saved to dataset_with_model_responses.csv.")