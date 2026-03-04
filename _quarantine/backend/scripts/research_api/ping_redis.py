import redis
try:
    r = redis.Redis(host='127.0.0.1', port=6379, socket_connect_timeout=5)
    print(f"Ping: {r.ping()}")
except Exception as e:
    print(f"Error: {e}")
