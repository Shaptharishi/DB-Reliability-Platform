
import redis

def get_connection(host, port, db=0):
    return redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True)

def check_memory_usage(conn):
    info = conn.info()

    used_memory = info.get('used_memory')
    maxmemory = info.get('maxmemory')

    if maxmemory == 0:
        percent_used = None
    else:
        percent_used = (used_memory/maxmemory) * 100

    return {'used_memory_bytes':used_memory, 'maxmemory_bytes':maxmemory, 'percent_used':round(percent_used,2) if percent_used is not None else None}

def check_eviction_policy(conn):
    config = conn.config_get('maxmemory-policy')
    policy = config.get('maxmemory-policy')

    return {'eviction_policy': policy, 'is_noeviction': policy =='noeviction'}

def check_clients_and_replication(conn):
    info = conn.info()

    return {'connected_clients':info.get('connected_clients'),
            'blocked_clients':info.get('blocked_clients'),
            'role':info.get('role'),
            'connected_slaves':info.get('connected_slaves',0)}


if __name__ == '__main__':
    conn = get_connection('localhost', 6379, 0)
    print(check_memory_usage(conn))
    print(check_eviction_policy(conn))
    print(check_clients_and_replication(conn))


