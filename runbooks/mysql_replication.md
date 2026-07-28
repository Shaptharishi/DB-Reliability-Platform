
# MySQL Replication Issues

Covers both replication thread failures (IO thread down) and 
replication lag (SQL thread falling behind).

## Symptoms
- `Replica_IO_Running` is not `Yes` → replication has stopped 
  entirely, not just slowed down
- `Seconds_Behind_Source` climbing steadily

## Likely Causes (most common first)
1. **IO thread down:** network connectivity issue between replica 
   and source, or authentication/credential failure
2. **SQL thread lagging (IO fine):** a large transaction being 
   replayed, disk I/O contention on the replica, or a single-threaded 
   replication apply bottleneck under heavy write load

## Diagnosis Steps
```sql
SHOW REPLICA STATUS\G
-- Check Replica_IO_Running and Replica_SQL_Running SEPARATELY --
-- they fail for different reasons and need different fixes

SHOW PROCESSLIST;
SELECT * FROM information_schema.innodb_trx ORDER BY trx_started ASC;
```

## Resolution
- **If IO thread is down:** verify network path and credentials 
  between replica and source; check source's max_connections 
  hasn't been exhausted by the replication connection itself
- **If SQL thread is lagging:** identify the specific large 
  transaction or resource bottleneck on the replica; in extreme 
  cases the replica may need to be rebuilt from a fresh backup 
  if lag has grown unmanageably large

## Prevention
- Use GTID-based replication for more resilient failover and 
  easier troubleshooting
- Size replicas with adequate disk I/O headroom for peak write volume
- Avoid extremely large single transactions on the source where possible
