import psycopg2
import time

connections = []

for i in range(85):
    conn = psycopg2.connect(
        host='postgres', port=5432,
        dbname='testdb1', user='postgres', password='pass'
    )
    connections.append(conn)

print(f"Opened {len(connections)} connections. Sleeping 30 seconds...")
time.sleep(30)

for conn in connections:
    conn.close()

print("Closed all connections.")
