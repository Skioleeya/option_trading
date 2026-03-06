import mmap
import struct
import numpy as np
import pyarrow as pa
from typing import Iterator, List
import logging

logger = logging.getLogger(__name__)

class InstitutionalMarketEvent:
    # C-packed struct format alignment (matches Rust's repr(C) with padding)
    # symbol(32) | seq_no(8) | event_type(1) | pad(7) | bid(8) | ask(8) | price(8) | spot(8) | vol(8) | oi(8) | iv(8) | impact(8) | sweep(1) | pad(7) | ttm(8) | mono(8) | id(8)
    STRUCT_FORMAT = "=32s Q B 7x d d d d Q Q d d ? 7x d Q Q"
    SIZE = struct.calcsize(STRUCT_FORMAT)

class RustBridge:
    def __init__(self, shm_path: str):
        self.shm_path = shm_path
        self.shm_fd = None
        self.mm = None
        self.head_ptr = 0
        self.tail_ptr = 64
        self.buffer_ptr = 128
        self.buffer_size = 1024 * 1024

    def connect(self) -> bool:
        """Attempt to connect to the shared memory mapping. Returns True if successful."""
        if self.mm:
            return True

        # On Windows, shared_memory crate uses named file mapping.
        # It typically exists in the 'Global\' namespace if created with high privileges,
        # or local namespace otherwise.
        path_variants = [self.shm_path, f"Global\\{self.shm_path}", f"Local\\{self.shm_path}"]
        
        logger.info(f"[RustBridge] Connecting to SHM. Path candidates: {path_variants}")
        
        for variant in path_variants:
            try:
                # We use mmap with tagname on Windows to open existing mapping
                # Length must match what the producer created.
                expected_len = self.buffer_size * InstitutionalMarketEvent.SIZE + 128
                self.mm = mmap.mmap(-1, expected_len, tagname=variant)
                self.mm_path = variant # Set for diag markers
                logger.info(f"[RustBridge] SUCCESS: Connected to Shared Memory via variant: {variant}")
                return True
            except PermissionError as e:
                logger.warning(f"[RustBridge] PERMISSION DENIED for variant '{variant}': {e} (WinError 5?)")
            except FileNotFoundError:
                logger.debug(f"[RustBridge] NOT FOUND: variant '{variant}' does not exist yet.")
            except Exception as e:
                logger.error(f"[RustBridge] FAILED: variant '{variant}' error: {e}")
        
        logger.warning(f"[RustBridge] FAILED to connect to any SHM candidates for path '{self.shm_path}'")
        return False

    def poll(self) -> Iterator[dict]:
        if not self.mm:
            return
        
        # Read tail (consumer's local head)
        self.mm.seek(self.tail_ptr)
        tail = struct.unpack("Q", self.mm.read(8))[0]
        
        # Read head (producer's head)
        self.mm.seek(self.head_ptr)
        head = struct.unpack("Q", self.mm.read(8))[0]
        
        while tail < head:
            offset = self.buffer_ptr + (tail % self.buffer_size) * InstitutionalMarketEvent.SIZE
            self.mm.seek(offset)
            data = self.mm.read(InstitutionalMarketEvent.SIZE)
            
            unpacked = struct.unpack(InstitutionalMarketEvent.STRUCT_FORMAT, data)
            yield {
                "symbol": unpacked[0].decode('utf-8', errors='replace').strip('\x00'),
                "seq_no": unpacked[1],
                "event_type": unpacked[2],
                "bid": unpacked[3],
                "ask": unpacked[4],
                "last_price": unpacked[5],
                "volume": unpacked[7],
                "impact_index": unpacked[10],
                "is_sweep": unpacked[11],
                "arrival_mono_ns": unpacked[13],
            }
            tail += 1
            
        # Update tail
        self.mm.seek(self.tail_ptr)
        self.mm.write(struct.pack("Q", tail))

    def to_arrow_batch(self, events: List[dict]) -> pa.RecordBatch:
        """Convert a list of raw event dicts to a pyarrow RecordBatch."""
        if not events:
            return None
            
        # Standardized Schema matching Rust side
        schema = pa.schema([
            ("symbol", pa.string()),
            ("seq_no", pa.uint64()),
            ("event_type", pa.uint8()),
            ("bid", pa.float64()),
            ("ask", pa.float64()),
            ("last_price", pa.float64()),
            ("volume", pa.uint64()),
            ("impact_index", pa.float64()),
            ("is_sweep", pa.bool_()),
            ("arrival_mono_ns", pa.uint64()),
        ])
        
        # Efficient column-wise construction
        arrays = {
            "symbol": [e["symbol"] for e in events],
            "seq_no": [e["seq_no"] for e in events],
            "event_type": [e["event_type"] for e in events],
            "bid": [e["bid"] for e in events],
            "ask": [e["ask"] for e in events],
            "last_price": [e["last_price"] for e in events],
            "volume": [e["volume"] for e in events],
            "impact_index": [e["impact_index"] for e in events],
            "is_sweep": [e["is_sweep"] for e in events],
            "arrival_mono_ns": [e["arrival_mono_ns"] for e in events],
        }
        
        return pa.RecordBatch.from_pydict(arrays, schema=schema)
