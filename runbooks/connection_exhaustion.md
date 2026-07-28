
# Connection Exhaustion

High connection usage relative to the configured maximum, 
risking new connections being refused.

## Symptoms
- `percent_used` metric above 80% (warning) or 95% (critical)
- Application errors: "too many connections" or "FATAL: sorry, 
  too many clients already"
- New client connections timing out or being rejected

## Likely Causes (most common first)
1. Application not using connection pooling — opening a new 
   connection per request instead of reusing a pool
2. Idle-in-transaction sessions holding connections open 
   without releasing them
3. A connection leak in application code (connections opened 
   but never closed on error paths)
4. Genuine legitimate traffic spike exceeding provisioned capacity

## Diagnosis Steps

**PostgreSQL:**
```sql
SELECT usename, application_name, state, count(*)
FROM pg_stat_activity
GROUP BY usename, application_name, state
ORDER BY count(*) DESC;
```
Identify which application/user is consuming the most connections.

**MySQL:**
```sql
SHOW PROCESSLIST;
SELECT * FROM information_schema.innodb_trx;
```

## Resolution
- If idle-in-transaction sessions are found, terminate them:
```sql
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity
  WHERE state = 'idle in transaction'
  AND now() - state_change > interval '10 minutes';
```
- If it's a genuine traffic spike, consider temporarily raising 
  `max_connections` (requires restart in PostgreSQL — plan 
  accordingly, not an instant fix)

## Prevention
- Implement connection pooling (PgBouncer for PostgreSQL) so the 
  application never needs as many real backend connections
- Set a statement timeout / idle-in-transaction timeout at the 
  database level to auto-kill stuck sessions
- Add connection pool size limits in the application itself
