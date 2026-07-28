from alerts.slack_notifier import send_slack_alert
import clickhouse_connect

def get_connection(host, port, username, password):
    return clickhouse_connect.get_client(
        host=host,
        port=port,
        username=username,
        password=password
    )

def ensure_tables_exist(client):
    client.command("CREATE DATABASE IF NOT EXISTS monitoring")

    client.command("""
        CREATE TABLE IF NOT EXISTS monitoring.metrics (
            ts DateTime DEFAULT now(),
            db_type String,
            db_host String,
            metric_name String,
            metric_value Float64
        ) ENGINE = MergeTree()
        ORDER BY (db_type, metric_name, ts)
    """)

    client.command("""
        CREATE TABLE IF NOT EXISTS monitoring.alerts (
            ts DateTime DEFAULT now(),
            rule String,
            severity String,
            db_type String,
            message String,
            runbook String
        ) ENGINE = MergeTree()
        ORDER BY (ts)
    """)

    print("[clickhouse] tables verified/created")

def write_metrics(client, db_type, db_host, metrics_dict):
    rows = []
    for metric_name, metric_value in metrics_dict.items():
        if metric_value is None:
            continue
        rows.append([db_type, db_host, metric_name, float(metric_value)])

    if len(rows) == 0:
        return

    client.insert(
        "monitoring.metrics",
        rows,
        column_names=["db_type", "db_host", "metric_name", "metric_value"]
    )

def write_alert(client, rule_result):
    if rule_result is None:
        return

    client.insert(
        "monitoring.alerts",
        [[
            rule_result.get("rule"),
            rule_result.get("severity"),
            rule_result.get("db_type", "unknown"),
            rule_result.get("message"),
            rule_result.get("runbook")
        ]],
        column_names=["rule", "severity", "db_type", "message", "runbook"]
    )
    
    send_slack_alert(rule_result)

if __name__ == "__main__":
    from collectors.postgres_collector import get_connection as pg_get_connection, check_connection_usage
    from rules.diagnostic_rules import rule_high_connection_usage

    ch_client = get_connection('localhost', 8123, 'default', 'ppass')

    pg = pg_get_connection('localhost', 5432, 'testdb1', 'postgres', 'pass')
    result = check_connection_usage(pg)

    write_metrics(ch_client, "postgresql", "localhost", result)

    alert = rule_high_connection_usage(result, "postgresql")
    write_alert(ch_client, alert)

    print("Done writing to ClickHouse")

