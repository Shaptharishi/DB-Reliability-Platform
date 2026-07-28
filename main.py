import os
import time

from collectors.postgres_collector import (
    get_connection as pg_connect,
    check_connection_usage as pg_conn_usage,
    check_replication_lag as pg_repl_lag,
    check_idle_transactions as pg_idle,
    check_table_bloat as pg_bloat,
)
from collectors.mysql_collector import (
    get_connection as mysql_connect,
    check_connection_usage as mysql_conn_usage,
    check_replication_status as mysql_repl,
    check_slow_queries as mysql_slow,
)
from collectors.redis_collector import (
    get_connection as redis_connect,
    check_memory_usage as redis_memory,
    check_eviction_policy as redis_eviction,
)
from rules.diagnostic_rules import (
    rule_high_connection_usage,
    rule_replica_lag_bytes,
    rule_idle_transactions,
    rule_table_bloat,
    rule_mysql_replication_lag,
    rule_slow_queries,
    rule_redis_memory,
    rule_redis_eviction_risk,
)
from storage.clickhouse_writer import get_connection as ch_connect, write_metrics, write_alert, ensure_tables_exist


PG_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", 5432)),
    "dbname": os.environ.get("POSTGRES_DB", "testdb1"),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "pass"),
}
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "database": os.environ.get("MYSQL_DB", "testdb1"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "pass"),
}
REDIS_CONFIG = {
    "host": os.environ.get("REDIS_HOST", "localhost"),
    "port": int(os.environ.get("REDIS_PORT", 6379)),
    "db": 0,
}
CLICKHOUSE_CONFIG = {
    "host": os.environ.get("CLICKHOUSE_HOST", "localhost"),
    "port": int(os.environ.get("CLICKHOUSE_PORT", 8123)),
    "username": os.environ.get("CLICKHOUSE_USER", "default"),
    "password": os.environ.get("CLICKHOUSE_PASSWORD", "ppass"),
} 

CHECK_INTERVAL_SECONDS = 30

def connect_with_retry(connect_func, config, name, max_retries=10, delay_seconds=5):
    for attempt in range(1, max_retries + 1):
        try:
            conn = connect_func(**config)
            print(f"[{name}] connected successfully")
            return conn
        except Exception as e:
            print(f"[{name}] connection attempt {attempt}/{max_retries} failed: {e}")
            time.sleep(delay_seconds)

    raise Exception(f"[{name}] could not connect after {max_retries} attempts")


def check_postgres(ch_client):
    try:
        conn = connect_with_retry(pg_connect, PG_CONFIG, "postgres", max_retries=5, delay_seconds=3)
    except Exception as e:
        print(f"[postgres] giving up this cycle: {e}")
        return

    try:
        conn_usage = pg_conn_usage(conn)
        write_metrics(ch_client, "postgresql", PG_CONFIG["host"], conn_usage)
        write_alert(ch_client, rule_high_connection_usage(conn_usage, "postgresql"))

        repl = pg_repl_lag(conn)
        write_alert(ch_client, rule_replica_lag_bytes(repl))

        idle = pg_idle(conn)
        write_alert(ch_client, rule_idle_transactions(idle))

        bloat = pg_bloat(conn)
        write_alert(ch_client, rule_table_bloat(bloat))

        print("[postgres] checks complete")

    except Exception as e:
        print(f"[postgres] error during checks: {e}")

    finally:
        conn.close()

def check_mysql(ch_client):
    try:
        conn = connect_with_retry(mysql_connect, MYSQL_CONFIG, "mysql", max_retries=5, delay_seconds=3)
    except Exception as e:
        print(f"[mysql] giving up this cycle: {e}")
        return

    try:
        conn_usage = mysql_conn_usage(conn)
        write_metrics(ch_client, "mysql", MYSQL_CONFIG["host"], conn_usage)
        write_alert(ch_client, rule_high_connection_usage(conn_usage, "mysql"))

        repl = mysql_repl(conn)
        write_alert(ch_client, rule_mysql_replication_lag(repl))

        slow = mysql_slow(conn)
        write_alert(ch_client, rule_slow_queries(slow))

        print("[mysql] checks complete")

    except Exception as e:
        print(f"[mysql] error during checks: {e}")

    finally:
        conn.close()


def check_redis(ch_client):
    try:
        conn = connect_with_retry(redis_connect, REDIS_CONFIG, "redis", max_retries=5, delay_seconds=3)
    except Exception as e:
        print(f"[redis] giving up this cycle: {e}")
        return

    try:
        mem = redis_memory(conn)
        write_metrics(ch_client, "redis", REDIS_CONFIG["host"], mem)
        write_alert(ch_client, rule_redis_memory(mem))

        evict = redis_eviction(conn)
        write_alert(ch_client, rule_redis_eviction_risk(mem, evict))

        print("[redis] checks complete")

    except Exception as e:
        print(f"[redis] error during checks: {e}")

def run_all_checks():
    ch_client = connect_with_retry(ch_connect, CLICKHOUSE_CONFIG, "clickhouse")

    check_postgres(ch_client)
    check_mysql(ch_client)
    check_redis(ch_client)


if __name__ == "__main__":
    print("Starting DB reliability monitor. Checking every", CHECK_INTERVAL_SECONDS, "seconds.")

    ch_client = connect_with_retry(ch_connect, CLICKHOUSE_CONFIG, "clickhouse")
    ensure_tables_exist(ch_client) 

    while True:
        run_all_checks()
        time.sleep(CHECK_INTERVAL_SECONDS)


