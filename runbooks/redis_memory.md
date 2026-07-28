
# Redis Memory Pressure

Redis memory usage is approaching or has reached the configured 
maxmemory limit, risking write rejections.

## Symptoms
- `percent_used` above 80% (warning) or 95% (critical)
- If `maxmemory-policy` is `noeviction`: write errors once the 
  limit is hit (`OOM command not allowed`)
- If an eviction policy is set: unexpected key disappearance 
  as Redis evicts data to make room

## Likely Causes (most common first)
1. No `maxmemory-policy` eviction strategy configured for a 
   pure-cache use case, combined with unbounded key growth
2. Missing TTLs on keys that should expire but never do
3. Genuine data growth exceeding the provisioned memory size
4. A single command or client bulk-inserting large values rapidly

## Diagnosis Steps
```bash
redis-cli CONFIG GET maxmemory-policy
redis-cli INFO keyspace
# compare "keys=X" vs "expires=Y" -- large gap means most
# keys have no TTL at all

redis-cli --bigkeys
```

## Resolution
- If this is meant to be a pure cache and `maxmemory-policy` is 
  `noeviction`, switch to `allkeys-lru`:
```bash
  redis-cli CONFIG SET maxmemory-policy allkeys-lru
```
- If keys are missing TTLs that should have them, fix at the 
  application level going forward
- If genuine data growth, increase `maxmemory` or scale the 
  instance

## Prevention
- Set an explicit, deliberate `maxmemory-policy` matching the 
  actual use case (cache vs durable store) rather than relying 
  on the `noeviction` default
- Ensure the application consistently sets TTLs on cache-only keys
