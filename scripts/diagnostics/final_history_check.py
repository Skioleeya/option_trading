import redis

def check_history():
    r = redis.Redis(host='localhost', port=6380, db=0)
    today = '20260305'
    key = f"app:atm_decay_series:{today}"
    length = r.llen(key)
    print(f"ATM History Length in Redis: {length}")
    
    # Try one sample to check size per item
    if length > 0:
        sample = r.lindex(key, 0)
        print(f"Sample item size: {len(sample) if sample else 0} bytes")

if __name__ == "__main__":
    check_history()
