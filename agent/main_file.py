import os
import json
from dotenv import load_dotenv
from groq import Groq
from fastapi import FastAPI
from pydantic import BaseModel
import uuid
import time
import clickhouse_connect
from tools import log_trace, CH_CONFIG 

from tools import health_check_tool, query_tool, rag_tool, metrics_tool, safe_json_dumps

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-120b"

# ---- Describing the tools to the model ----
# This is a description of CAPABILITIES, not code. The model
# never sees the actual Python functions -- only this schema.
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "health_check_tool",
            "description": "Checks current PostgreSQL health: connection usage percentage and any idle-in-transaction sessions.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_tool",
            "description": "Runs a read-only SQL SELECT query against the PostgreSQL database to answer questions about real data such as customers and orders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "A single, safe, read-only SELECT statement."
                    }
                },
                "required": ["sql_query"]
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "rag_tool",
        "description": "Searches internal runbooks for guidance on diagnosing and resolving a specific database issue.",
        "parameters": {
            "type": "object",
            "properties": {
                "query_text": {
                    "type": "string",
                    "description": "A description of the issue to find relevant runbook guidance for."
                }
            },
            "required": ["query_text"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "metrics_tool",
        "description": "Retrieves historical trend data for a specific PostgreSQL metric over a recent time window, to see how it has changed over time.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric_name": {
                    "type": "string",
                    "description": "The metric to retrieve, e.g. 'connection_percent_used'."
                },
                "minutes_back": {
                    "type": "integer",
                    "description": "How many minutes of history to retrieve. Defaults to 60."
                }
            },
            "required": ["metric_name"]
        }
    }
}
]

# ---- The bridge between "text saying call this tool" and
# ---- "actually calling the real Python function" ----
AVAILABLE_TOOLS = {
    "health_check_tool": lambda args: health_check_tool(),
    "query_tool": lambda args: query_tool(args["sql_query"]),
    "rag_tool": lambda args: rag_tool(args["query_text"]),
    "metrics_tool": lambda args: metrics_tool(args["metric_name"], args.get("minutes_back", 60)),
}


def run_agent(user_question, max_iterations=8):
    trace_id = str(uuid.uuid4())
    trace_client = clickhouse_connect.get_client(**CH_CONFIG)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a PostgreSQL database troubleshooting assistant. "
                "Choose the tool that most directly fits the question: "
                "use health_check_tool for current connection/transaction "
                "health, query_tool for questions about actual data like "
                "customers or orders, metrics_tool for historical trends, "
                "and rag_tool only when you need guidance on diagnosing or "
                "resolving a specific KNOWN problem or symptom. "
                "Note: the pg_stat_statements extension is NOT installed in "
                "this environment -- do not attempt to query it. When "
                "examining pg_stat_activity, exclude your own session using "
                "AND pid <> pg_backend_pid()."
            )
        },
        {"role": "user", "content": user_question}
    ]

    try:
        for iteration in range(max_iterations):
            start_time = time.time()

            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )

            latency_ms = (time.time() - start_time) * 1000
            tokens_used = response.usage.total_tokens if response.usage else 0

            message = response.choices[0].message

            log_trace(
                trace_client, trace_id, iteration + 1, "reason",
                tokens_used=tokens_used, latency_ms=latency_ms
            )

            if message.tool_calls:
                messages.append(message)

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    tool_start = time.time()

                    if tool_name in AVAILABLE_TOOLS:
                        result = AVAILABLE_TOOLS[tool_name](tool_args)
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}

                    tool_latency_ms = (time.time() - tool_start) * 1000

                    log_trace(
                        trace_client, trace_id, iteration + 1, "tool_call",
                        tool_name=tool_name,
                        tool_args=json.dumps(tool_args),
                        tool_result=json.dumps(result)[:2000],  # cap length
                        latency_ms=tool_latency_ms
                    )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

                continue

            else:
                log_trace(
                    trace_client, trace_id, iteration + 1, "final_answer",
                    tool_result=message.content[:2000]
                )
                return message.content

        return "Reached max reasoning iterations without a final answer."

    finally:
        trace_client.close()


app = FastAPI()


class Question(BaseModel):
    question: str


@app.post("/ask")
def ask(q: Question):
    answer = run_agent(q.question)
    return {"answer": answer}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)