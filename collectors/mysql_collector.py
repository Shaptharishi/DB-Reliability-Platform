
import mysql.connector


def get_connection(host, port, database, user, password):
    return mysql.connector.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password ) 


def check_connection_usage(conn):
    cur = conn.cursor()
    cur.execute("SHOW STATUS LIKE 'Threads_connected';")
    result = cur.fetchone()
    current = int(result[1])

    cur.execute("SHOW VARIABLES LIKE 'max_connections';")
    result2 = cur.fetchone()
    max_conn = int(result2[1])

    if max_conn == 0:
        percent_used = 0
    else:
        percent_used = (current/max_conn) * 100

    cur.close()

    return {'current':current, 'max_conn':max_conn, 'percent_used': round(percent_used, 2)}


def check_replication_status(conn):
    cur = conn.cursor()
    cur.execute("SHOW REPLICA STATUS;")
    row = cur.fetchone()
    cur.close()

    if row is None:
        return {'is_replica':False}

    columns = [desc[0] for desc in cur.description]
    row_dict = dict(zip(columns, row))

    return {'is_replica':True,
            'io_running':row_dict.get('Replica_IO_Running'),
            'sql_running':row_dict.get('Replica_SQL_Running'),
            'seconds_behind_source':row_dict.get('Seconds_Behind_Source') } 


def check_slow_queries(conn):
    cur = conn.cursor()
    cur.execute(""" SELECT digest_text, count_star, avg_timer_wait/1000000000 as avg_ms
                    FROM performance_schema.events_statements_summary_by_digest
                    ORDER BY avg_timer_wait desc
                    LIMIT 5; """)
    rows = cur.fetchall()
    cur.close()

    slow_queries = []
    for row in rows:
        slow_queries.append({'query_pattern':row[0], 'times_executed':row[1], 'avg_ms':float(row[2] if row[2] is not None else 0.0)})

    return {'slow_queries':slow_queries}


def check_innodb_transactions(conn):
    cur = conn.cursor()
    cur.execute(""" SELECT trx_id, trx_state, trx_started, trx_query
                    FROM information_schema.innodb_trx; """)
    rows = cur.fetchall()
    cur.close()

    active_transactions = []
    for row in rows:
        active_transactions.append({'trx_id':row[0],
                                    'trx_state':row[1],
                                    'trx_started':str(row[2]),
                                    'query':row[3]})

    return {'count':len(active_transactions), 'active_transactions':active_transactions}

if __name__ == '__main__':
    conn = get_connection('127.0.0.1', 3306, 'testdb1', 'root', 'pass')
    print(check_connection_usage(conn))
    print(check_replication_status(conn))
    print(check_slow_queries(conn))
    print(check_innodb_transactions(conn))



