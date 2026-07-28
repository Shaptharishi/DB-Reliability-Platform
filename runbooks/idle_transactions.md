
# Idle-in-Transaction Sessions

One or more database sessions have an open transaction that has 
been sitting idle for an extended period, without committing 
or rolling back.

## Symptoms
- Sessions in `idle in transaction` state for several minutes
- VACUUM/autovacuum unable to clean up dead tuples on unrelated 
  tables (a stuck old transaction blocks cleanup database-wide)
- Table bloat growing even on tables that aren't being actively 
  modified

## Likely Causes (most common first)
1. Application opened a transaction (BEGIN) and crashed or hung 
   before COMMIT/ROLLBACK
2. A developer left a `psql`/`mysql` session open mid-transaction
3. Application-level bug not properly closing transactions on 
   error paths

## Diagnosis Steps

**PostgreSQL:**
```sql
SELECT pid, now() - xact_start AS duration, query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
ORDER BY duration DESC;
```

## Resolution
- For sessions idle beyond a reasonable threshold (e.g. 10+ minutes 
  with no clear reason), terminate them:
```sql
  SELECT pg_terminate_backend(<pid>);
```
- Investigate the originating application/script to understand 
  why the transaction was left open

## Prevention
- Set `idle_in_transaction_session_timeout` at the database level 
  to auto-kill sessions stuck idle-in-transaction beyond a limit
- Review application code for transaction blocks missing proper 
  try/finally or equivalent cleanup on error
