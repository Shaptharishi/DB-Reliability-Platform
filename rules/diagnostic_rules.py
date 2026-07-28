
from collectors.postgres_collector import get_connection, check_connection_usage, check_replication_lag


def rule_high_connection_usage(collector_result, db_type):
    percent = collector_result.get('percent_used')

    if percent is None:
        return None

    if percent >= 95:
        severity = 'critical'
    elif percent >= 80:
        severity = 'warning'
    else:
        return None

    return {'rule':'high_connection_usage',
            'severity':severity,
            'db_type':db_type,
            'message':f"Connection usage at {percent}% ({collector_result.get('current')}/{collector_result.get('max_conn')})",
            'runbook':'runbooks/connection_exhaustion.md'}

def rule_replica_lag_bytes(collector_result):
    has_replicas = collector_result.get('has_replicas')

    if has_replicas is False:
        return None

    replicas = collector_result.get('replicas')

    for replica in replicas:
        lag = replica.get('lag_bytes')

        if lag > 50000000:
            return {'rule':'replica_lag_bytes',
                    'severity':'warning',
                    'replica':replica.get('client_addr'),
                    'lag_bytes':lag,
                    'message': f"Replica {replica.get('client_addr')} is {lag} bytes behind (threshold: 50000000)",
                    'runbook': 'runbooks/replication_lag.md'}

    return None

def rule_idle_transactions(collector_result):
    sessions = collector_result.get('stuck_sessions',[])

    long_idle = [s for s in sessions if s.get('duration_seconds',0) > 300]

    if len(long_idle) == 0:
        return None

    worst = max(long_idle, key=lambda s: s['duration_seconds'])

    return {'rule': 'idle_in_transaction',
            'severity': 'warning',
            'message': f"{len(long_idle)} sessions idle-in-transaction over 5min. Worst PID {worst['pid']} at {round(worst['duration_seconds'])}s",
            'runbook': 'runbooks/idle_transactions.md'}

def rule_table_bloat(collector_result):
    tables = collector_result.get('tables', [])

    bloated = [
        t for t in tables
        if t.get('dead_percent', t.get('dead_pct', 0)) > 20
        and (t.get('live_tuples', 0) + t.get('dead_tuples', 0)) > 1000
    ]

    if len(bloated) == 0:
        return None

    return {
        "rule": "table_bloat",
        "severity": "warning",
        "message": f"{len(bloated)} table(s) with over 20% dead tuples: {[t.get('table_name', t.get('table')) for t in bloated]}",
        "runbook": "runbooks/table_bloat.md"
    }

def rule_mysql_replication_lag(collector_result):
    if not collector_result.get('is_replica'):
        return None

    io_running = collector_result.get('io_running')
    seconds_behind = collector_result.get('seconds_behind_source')

    if io_running != 'Yes':
        return {
            "rule": "mysql_replication_io_down",
            "severity": "critical",
            "message": f"MySQL replica IO thread is not running (status: {io_running}) -- likely a network/connectivity issue to the source",
            "runbook": "runbooks/mysql_replication.md"
        }

    if seconds_behind is not None and seconds_behind > 60:
        return {
            "rule": "mysql_replication_lag",
            "severity": "warning",
            "message": f"MySQL replica is {seconds_behind}s behind source",
            "runbook": "runbooks/mysql_replication.md"
        }

    return None

def rule_slow_queries(collector_result):
    slow = [
        q for q in collector_result.get('slow_queries', [])
        if q.get('avg_ms', 0) > 1000 and q.get('times_executed', 0) > 3
    ]

    if len(slow) == 0:
        return None

    return {
        "rule": "slow_queries",
        "severity": "warning",
        "message": f"{len(slow)} recurring query pattern(s) averaging over 1000ms",
        "runbook": "runbooks/slow_queries.md"
    }


def rule_redis_memory(collector_result):
    percent = collector_result.get('percent_used')

    if percent is None:
        return None

    if percent > 80:
        return {
            "rule": "redis_memory_high",
            "severity": "warning" if percent < 95 else "critical",
            "message": f"Redis memory usage at {percent}%",
            "runbook": "runbooks/redis_memory.md"
        }

    return None


def rule_redis_eviction_risk(memory_result, eviction_result):
    percent = memory_result.get('percent_used')
    is_noeviction = eviction_result.get('is_noeviction')

    if percent is None or percent < 80:
        return None

    if is_noeviction:
        return {
            "rule": "redis_eviction_risk",
            "severity": "critical",
            "message": f"Memory at {percent}% AND eviction policy is 'noeviction' -- writes will start failing once memory limit is hit",
            "runbook": "runbooks/redis_memory.md"
        }

    return None


if __name__ == "__main__":
    from collectors.postgres_collector import (
        get_connection as pg_conn, check_connection_usage as pg_conn_check,
        check_replication_lag, check_idle_transactions, check_table_bloat
    )
    from collectors.mysql_collector import (
        get_connection as mysql_conn, check_connection_usage as mysql_conn_check,
        check_replication_status, check_slow_queries
    )
    from collectors.redis_collector import (
        get_connection as redis_conn, check_memory_usage, check_eviction_policy
    )

    pg = pg_conn('localhost', 5432, 'testdb1', 'postgres', 'pass')
    print(rule_high_connection_usage(pg_conn_check(pg), "postgresql"))
    print(rule_replica_lag_bytes(check_replication_lag(pg)))
    print(rule_idle_transactions(check_idle_transactions(pg)))
    print(rule_table_bloat(check_table_bloat(pg)))

    my = mysql_conn('127.0.0.1', 3306, 'testdb1', 'root', 'pass')
    print(rule_high_connection_usage(mysql_conn_check(my), "mysql"))
    print(rule_mysql_replication_lag(check_replication_status(my)))
    print(rule_slow_queries(check_slow_queries(my)))

    rd = redis_conn('localhost', 6379, 0)
    mem = check_memory_usage(rd)
    evict = check_eviction_policy(rd)
    print(rule_redis_memory(mem))
    print(rule_redis_eviction_risk(mem, evict))




