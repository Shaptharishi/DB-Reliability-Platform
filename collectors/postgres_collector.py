
import psycopg2

def get_connection(host, port, dbname, user, password):
    return psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
    )

def check_connection_usage(conn):
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM pg_stat_activity;')
    result = cur.fetchone()
    current = result[0]

    cur.execute('SHOW max_connections;')
    result2 = cur.fetchone()
    max_conn = int(result2[0])

    if max_conn == 0:
        percent_used = 0
    else:
        percent_used = (current/max_conn) * 100

    cur.close()

    result_dict = {'current':current, 'max_conn':max_conn, 'percent_used':percent_used}

    return result_dict


def check_replication_lag(conn):
    cur = conn.cursor()
    cur.execute('SELECT client_addr, state, pg_wal_lsn_diff(sent_lsn, replay_lsn) as lag_bytes FROM pg_stat_replication;')
    rows = cur.fetchall()
    cur.close()

    if len(rows) == 0:
        return {'has_replica': False, 'replicas':[]}

    replicas = []
    for row in rows:
        replica_info = {'client_addr':row[0], 'state':row[1], 'lag_bytes':row[2]}
        replicas.append(replica_info)
    
    return {'has_replica':True, 'replicas':replicas}


def check_idle_transactions(conn):
    cur = conn.cursor()
    cur.execute("""
                SELECT pid, now() - xact_start as duration, query
                FROM pg_stat_activity
                WHERE state = 'idle in transaction'
                ORDER BY duration DESC; """)
    rows = cur.fetchall()
    cur.close()

    stuck_sessions = []
    for row in rows:
        session_info = {'pid':row[0], 'duration_seconds':row[1].total_seconds(), 'query':row[2]}
        stuck_sessions.append(session_info)

    return {'count':len(stuck_sessions), 'stuck_sessions':stuck_sessions}

def check_table_bloat(conn):
    cur = conn.cursor()
    cur.execute("""
                SELECT relname, n_live_tup, n_dead_tup
                FROM pg_stat_user_tables
                ORDER BY n_dead_tup
                LIMIT 10; """)
    rows = cur.fetchall()
    cur.close()

    tables = []
    for row in rows:
        relname = row[0]
        live = row[1]
        dead = row[2]
        total = live + dead

        if total == 0:
            dead_percent = 0
        else:
            dead_percent = (dead/total) * 100

        tables.append({'table_name':relname, 'live_tuples':live, 'dead_tuples':dead, 'dead_percent':round(dead_percent, 2)})

    return {'tables':tables}

if __name__ == '__main__':
    conn = get_connection('localhost', 5432, 'testdb1', 'postgres', 'pass')
    print(check_connection_usage(conn))
    print(check_replication_lag(conn))
    print(check_idle_transactions(conn))
    print(check_table_bloat(conn))
