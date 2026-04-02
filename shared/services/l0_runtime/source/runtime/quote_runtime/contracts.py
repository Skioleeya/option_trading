from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, Iterable, Protocol

from longport.openapi import SubType


class L0QuoteRuntime(Protocol):
    @property
    def event_queue(self) -> asyncio.Queue[Any]: ...

    @property
    def shm_path(self) -> str: ...

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def subscribe(
        self,
        symbols: Iterable[str],
        sub_types: list[SubType] | None = None,
    ) -> None: ...

    async def quote(self, symbols: list[str]) -> list[Any]: ...

    async def option_quote(self, symbols: list[str]) -> list[Any]: ...

    async def option_chain_info_by_date(self, symbol: str, expiry: date) -> list[Any]: ...

    async def calc_indexes(self, symbols: list[str], indexes: list[Any]) -> list[Any]: ...

    def diagnostics(self) -> dict[str, Any]: ...
