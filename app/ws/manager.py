"""App-wide WebSocket connection manager."""

from fastapi import WebSocket

class WSManager:
    """Stateholder for active WebSocket clients."""
    
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    def register(self, ws: WebSocket) -> None:
        self._clients.add(ws)

    def unregister(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    @property
    def clients(self) -> frozenset[WebSocket]:
        """Return an immutable snapshot of current connected clients."""
        return frozenset(self._clients)
