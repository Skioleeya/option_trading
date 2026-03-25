import mmap
import struct
import time

def check_shm():
    try:
        mm = mmap.mmap(-1, 1048576 * 168 + 128, tagname="Global\\Option_v3_L0_SHM")
    except Exception as e:
        print(f"Failed to open Global: {e}")
        try:
            mm = mmap.mmap(-1, 1048576 * 168 + 128, tagname="Option_v3_L0_SHM")
        except Exception as e2:
            print(f"Failed to open Local: {e2}")
            return
    
    head = struct.unpack("Q", mm[0:8])[0]
    tail = struct.unpack("Q", mm[64:72])[0]
    event_size = struct.unpack("<I", mm[24:28])[0]
    schema_version = struct.unpack("<I", mm[20:24])[0]
    
    print(f"SHM Config: Head={head}, Tail={tail}, EventSize={event_size}, Version={schema_version}")
    
    if head == 0:
        print("No events in SHM.")
        return

    # Check the last 5 events
    start_idx = max(0, head - 5)
    for i in range(start_idx, head):
        offset = 128 + (i % 1048576) * event_size
        data = mm[offset:offset+event_size]
        
        # Print raw bytes of the first 40 bytes to see the symbol and seq_no
        raw_hex = data[:40].hex()
        
        try:
            unpd = struct.unpack("=32s Q B 7x d d d d Q Q d d ? 7x d Q Q Q d d", data)
            sym = unpd[0].decode("utf-8", "replace").strip("\x00")
            print(f"Event {i}: sym={repr(sym)}, hex={raw_hex}")
        except Exception as e:
            print(f"Event {i} unpack failed: {e}")

if __name__ == "__main__":
    check_shm()
