
# Recurring Slow Queries

A query pattern is consistently running slower than expected 
across multiple executions (not a one-off outlier).

## Symptoms
- A query pattern averaging over 1000ms, executed repeatedly
- Application-level timeouts or slow page loads correlating with 
  specific database operations

## Likely Causes (most common first)
1. Missing index on a column used in WHERE/JOIN/ORDER BY
2. Stale table statistics causing the query planner to choose a 
   poor execution plan
3. Table growth has crossed a threshold where a previously-fine 
   query pattern no longer scales
4. Lock contention from another session blocking this query

## Diagnosis Steps

**MySQL:**
```sql
EXPLAIN <the query in question>;
-- look for type = ALL (full table scan)

SHOW INDEX FROM <table_name>;
ANALYZE TABLE <table_name>;
```

**PostgreSQL:**
```sql
EXPLAIN ANALYZE <the query in question>;
-- look for Seq Scan on a large table
```

## Resolution
- If no relevant index exists, create one matching the query's 
  actual filter/join columns
- If statistics are stale, refresh them (`ANALYZE` in both 
  Postgres and MySQL)
- If a lock is blocking the query, identify and resolve the 
  blocking session

## Prevention
- Review new queries for proper indexing before they reach 
  production, as part of code review
- Periodically review `pg_stat_statements` / `performance_schema` 
  for emerging slow patterns before they become customer-visible
