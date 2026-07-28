
# Table Bloat

A table has accumulated a high percentage of dead tuples, wasting 
disk space and slowing down queries against it.

## Symptoms
- `dead_pct` above 20% on a table with meaningful row count
- Table's on-disk size much larger than its actual live data would 
  suggest
- Query performance degrading over time on a specific table

## Likely Causes (most common first)
1. Autovacuum falling behind on a high-write-volume table
2. A long-running/idle-in-transaction session blocking vacuum 
   from reclaiming space (see idle_transactions.md)
3. `autovacuum_vacuum_scale_factor` too high for a very large table
4. Autovacuum disabled on this specific table

## Diagnosis Steps
```sql
SELECT relname, last_vacuum, last_autovacuum, n_dead_tup, n_live_tup
FROM pg_stat_user_tables
WHERE relname = '<table_name>';

-- Check for blocking long-running transactions
SELECT pid, now() - xact_start AS duration, state, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Check autovacuum settings on this specific table
SELECT relname, reloptions FROM pg_class WHERE relname = '<table_name>';
```

## Resolution
- Run a manual VACUUM to reclaim space immediately:
```sql
  VACUUM ANALYZE <table_name>;
```
- If space must be physically reclaimed (not just marked reusable), 
  `VACUUM FULL` is required — but this locks the table entirely; 
  schedule during a maintenance window, never during peak hours
- If a blocking transaction was found, resolve it first (see 
  idle_transactions.md), then re-run VACUUM

## Prevention
- Tune `autovacuum_vacuum_scale_factor` down for very large tables 
  (e.g. 0.01 instead of the 0.2 default)
- Ensure `autovacuum_max_workers` is sufficient for the number of 
  actively-written tables
- Monitor for long-running/idle-in-transaction sessions continuously
