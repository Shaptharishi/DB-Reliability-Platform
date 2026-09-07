import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, date, timedelta
from sentence_transformers import SentenceTransformer
import clickhouse_connect 
import re 
from decimal import Decimal 
import json 
import uuid
import time 

_embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def _json_safe(value):
    """
    Converts values psycopg2 returns that json.dumps() can't
    handle natively (datetime, date) into plain strings.
    Anything else passes through unchanged.
    """
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Decimal):
        return float(value)
    return value

def safe_json_dumps(obj):
    """
    A genuinely defensive alternative to plain json.dumps():
    instead of only pre-converting known problem types via
    _json_safe(), this catches ANY type json.dumps() doesn't
    understand and converts it to a plain string as a last
    resort, guaranteeing this specific crash can never happen
    again, even for a type not yet discovered.
    """
    return json.dumps(obj, default=str)

load_dotenv()

PG_CONFIG = {
    "host": os.environ.get("PG_HOST"),
    "port": int(os.environ.get("PG_PORT")),
    "dbname": os.environ.get("PG_DB"),
    "user": os.environ.get("PG_USER"),
    "password": os.environ.get("PG_PASSWORD"),
}


def get_connection(host, port, dbname, user, password):
    return psycopg2.connect(
        host=host, 
        port=port, 
        dbname=dbname,
        user=user, 
        password=password)


def check_connection_usage(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pg_stat_activity;")
    current = cur.fetchone()[0]
    cur.execute("SHOW max_connections;")
    max_conn = int(cur.fetchone()[0])
    percent_used = 0 if max_conn == 0 else (current / max_conn) * 100
    cur.close()
    return {"current": current, "max_conn": max_conn, "percent_used": percent_used}


def check_idle_transactions(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT pid, now() - xact_start AS duration, query
        FROM pg_stat_activity
        WHERE state = 'idle in transaction'
        ORDER BY duration DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    
    stuck_sessions = []
    for row in rows:
        session_info = {'pid':row[0], 'duration_seconds':row[1].total_seconds(), 'query':row[2]}
        stuck_sessions.append(session_info)
    
    return {'count':len(stuck_sessions), 'stuck_sessions':stuck_sessions}


# ---- The actual TOOL function the agent will call ----

def health_check_tool():
    """
    Opens a connection, runs both real checks, closes the
    connection, and returns a plain dictionary the agent can
    reason over.
    """
    conn = get_connection(**PG_CONFIG)
    try:
        return {
            "connection_usage": check_connection_usage(conn),
            "idle_transactions": check_idle_transactions(conn)
        }
    finally:
        conn.close()

FORBIDDEN_KEYWORDS = ["DELETE", "DROP", "UPDATE", "ALTER", "TRUNCATE", "INSERT", "GRANT", "REVOKE"]

def _is_query_safe(sql_text):
    """
    Layer 1 of defense against prompt injection (Phase 2):
    reject anything that isn't a plain SELECT, and reject
    anything containing a destructive keyword, BEFORE the query
    ever reaches the database.
    """
    upper_sql = sql_text.strip().upper()
    if not upper_sql.startswith("SELECT"):
        return False
    for word in FORBIDDEN_KEYWORDS:
        # \b means "word boundary" -- this matches GRANT as a
        # standalone word, but NOT as part of GRANTED, GRANTOR,
        # or any other longer word containing the same letters
        if re.search(r'\b' + word + r'\b', upper_sql):
            return False
    return True

def query_tool(sql_query):
    """
    Runs LLM-generated SQL using the READ-ONLY database user.
    Layer 2 of defense: even if _is_query_safe() somehow missed
    something, this database user has no permission to actually
    do damage.
    """
    if not _is_query_safe(sql_query):
        return {"error": "Query rejected: only plain SELECT statements are allowed."}

    conn = psycopg2.connect(
        host=os.environ.get("PG_HOST"),
        port=int(os.environ.get("PG_PORT")),
        dbname=os.environ.get("PG_DB"),
        user=os.environ.get("PG_READONLY_USER"),
        password=os.environ.get("PG_READONLY_PASSWORD"),
    )
    try:
        cur = conn.cursor()
        cur.execute(sql_query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        cur.close()
        results = [
            {col: _json_safe(val) for col, val in zip(columns, row)}
            for row in rows
        ]
        return {"results": results}
    except Exception as e:
        return {"error": f"Query failed: {str(e)}"}
    finally:
        conn.close()

def rag_tool(query_text):
    """
    Embeds the query, searches pgvector for the most similar
    runbook chunks, and returns the real retrieved text -- the
    actual RAG pipeline from Phase 4, now working code.
    """
    query_embedding = _embedding_model.encode(query_text).tolist()

    conn = get_connection(**PG_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT source_file, section, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM runbook_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT 3;
            """,
            (query_embedding, query_embedding)
        )
        rows = cur.fetchall()
        cur.close()
        return {
            "retrieved_chunks": [
                {"source": r[0], "section": r[1], "content": r[2], "similarity": round(r[3], 3)}
                for r in rows
            ]
        }
    finally:
        conn.close()

CH_CONFIG = {
    "host": os.environ.get("CH_HOST", "localhost"),
    "port": int(os.environ.get("CH_PORT", 8124)),
    "username": "default",
    "password": "agentpass",
    "database": "agent_metrics",
}


def metrics_tool(metric_name, minutes_back=60):
    """
    Queries real historical metric data from ClickHouse, showing
    the trend over a specified recent time window.
    """
    client = clickhouse_connect.get_client(**CH_CONFIG)
    try:
        result = client.query(
            f"""
            SELECT ts, metric_value
            FROM postgres_metrics
            WHERE metric_name = %(metric_name)s
              AND ts >= now() - INTERVAL {int(minutes_back)} MINUTE
            ORDER BY ts
            """,
            parameters={"metric_name": metric_name}
        )
        rows = [{"timestamp": str(r[0]), "value": r[1]} for r in result.result_rows]
        if not rows:
            return {
                "metric": metric_name,
                "data_points": [],
                "note": f"No data found for '{metric_name}'. Available metrics: connection_percent_used."
            }
        return {"metric": metric_name, "data_points": rows}
    except Exception as e:
        return {"error": f"Metrics query failed: {str(e)}"}
    finally:
        client.close()

def log_trace(client, trace_id, step_number, step_type, tool_name="", tool_args="", tool_result="", tokens_used=0, latency_ms=0.0):
    """
    Writes one real step of the agent's reasoning loop into
    ClickHouse. Never allowed to crash the actual agent if
    logging itself fails -- tracing is a supporting concern,
    not something that should ever break the real user-facing answer.
    """
    try:
        client.insert(
            "agent_traces",
            [[trace_id, step_number, step_type, tool_name, tool_args, tool_result, tokens_used, latency_ms]],
            column_names=["trace_id", "step_number", "step_type", "tool_name", "tool_args", "tool_result", "tokens_used", "latency_ms"]
        )
    except Exception as e:
        print(f"[tracing] failed to log trace step: {e}")