import redis
try:
    r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
    keys = r.keys("*")
    print(f"Total Keys: {len(keys)}")
    for k in keys[:50]: # Show first 50
        print(f" - {k} (Type: {r.type(k)})")
except Exception as e:
    print(f"Error: {e}")
