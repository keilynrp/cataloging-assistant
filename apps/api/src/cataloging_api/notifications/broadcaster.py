import asyncio


class NotificationBroadcaster:
    """In-process fan-out of "a newer cursor exists" signals to open WebSocket connections.

    The outbox in PostgreSQL is the durable, cross-process source of truth (the
    sync CLI, the API's own mutation endpoints, and this process's background
    publisher may all produce events); this broadcaster only relays the resulting
    cursor to sockets held open by *this* API process, per VERTICAL-014 principle 2:
    the socket never carries a notification body, only a monotonic cursor.
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[int]] = set()
        self._cursor = 0

    @property
    def cursor(self) -> int:
        return self._cursor

    def subscribe(self) -> asyncio.Queue[int]:
        queue: asyncio.Queue[int] = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[int]) -> None:
        self._subscribers.discard(queue)

    def publish(self, cursor: int) -> None:
        if cursor <= self._cursor:
            return
        self._cursor = cursor
        for queue in list(self._subscribers):
            if queue.full():
                continue
            queue.put_nowait(cursor)


broadcaster = NotificationBroadcaster()
