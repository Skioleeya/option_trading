"""Arrow IPC batch helpers for L0 runtime ingestion."""

from __future__ import annotations

from typing import Any, Iterator

import pyarrow as pa


def iter_arrow_batch_rows(batch: pa.RecordBatch) -> Iterator[dict[str, Any]]:
    """Yield Arrow batch rows as lightweight dict mappings for event normalization."""
    column_names = list(batch.schema.names)
    columns = [batch.column(index) for index in range(batch.num_columns)]
    for row_index in range(batch.num_rows):
        yield {
            name: column[row_index].as_py()
            for name, column in zip(column_names, columns, strict=False)
        }


def batch_id_from_batch(batch: pa.RecordBatch) -> int | None:
    """Return the batch id if present in the Arrow schema."""
    if batch.num_rows <= 0 or "batch_id" not in batch.schema.names:
        return None
    batch_id = batch.column(batch.schema.get_field_index("batch_id"))[0].as_py()
    if batch_id is None:
        return None
    return int(batch_id)
