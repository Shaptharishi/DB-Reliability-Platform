
# Replication Lag

A replica has fallen behind the primary in applying changes, 
risking stale reads or data loss on failover.

## Symptoms
- `lag_bytes` (PostgreSQL) or `Seconds_Behind_Source` (MySQL) 
  above threshold
- Reports/dashboards reading from a replica show outdated data
- Customers report "my data changed but the read replica shows 
  the old value"

## Likely Causes (most common first)
1. Network slowness between primary and replica
2. Replica under-provisioned (CPU/disk I/O) relative to write volume
3. A long-running query on the replica blocking WAL replay
4. Primary generating changes faster than the replica can apply 
   (large bulk load/migration)

## Diagnosis Steps

**PostgreSQL (run on the primary):**
```sql
SELECT client_addr, state,
       pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes
FROM pg_stat_replication;
```

**MySQL (run on the replica) — check BOTH threads separately:**
```sql
SHOW REPLICA STATUS\G
-- Replica_IO_Running: is the network connection healthy?
-- Replica_SQL_Running: is it actively applying changes?
-- Seconds_Behind_Source: how far behind
```

## Resolution
- If `Replica_IO_Running` is No → this is a network/connectivity 
  issue, not an apply issue. Check firewall rules and network path.
- If IO is fine but lag keeps growing → check for a long-running 
  query on the replica blocking replay, or replica resource 
  constraints (CPU, disk I/O)
- If caused by a known bulk load on the primary → this is often 
  self-resolving once the bulk operation finishes

## Prevention
- Size replicas with adequate headroom above expected write volume
- Avoid running heavy analytical queries directly against a 
  replica also used for real-time reads
- Monitor lag continuously (this system does), alert before it 
  becomes customer-visible
