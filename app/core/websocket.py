import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger("app.core.websocket")


class ConnectionManager:

    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = {}
        self.socket_rooms: dict[WebSocket, set[str]] = {}

 # ── Helpers privados ──────────────────────────────────────────────────────

    async def _send_to_rooms(self, rooms: list[str], payload: dict[str, Any]) -> None:
        sent_to: set[WebSocket] = set()

        for room in rooms:
            for connection in list(self.rooms.get(room, set())):

                if connection in sent_to:
                    continue

                try:
                    await connection.send_json(payload)
                    sent_to.add(connection)
                except Exception as e:
                    logger.warning(f"Error al enviar WebSocket. Removiendo conexión: {e}")
                    self.disconnect(connection)

 # ──────────────────────────────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, roles: list[str], user_id: int) -> None:
        await websocket.accept()

        for role in roles:
            self._join_room(websocket, f"role:{role.lower()}")

        self._join_room(websocket, f"user:{user_id}")

        logger.info(
            f"WS aceptado. user_id={user_id}, roles={roles}. "
            f"Total rooms activas: {len(self.rooms)}"
        )

    def disconnect(self, websocket: WebSocket) -> None:
        rooms = self.socket_rooms.pop(websocket, set())

        for room in rooms:

            if room in self.rooms:
                self.rooms[room].discard(websocket)

                if not self.rooms[room]:
                    del self.rooms[room]

        logger.info(
            f"Conexión WebSocket finalizada. Rooms liberadas: {rooms}. "
            f"Total rooms activas: {len(self.rooms)}"
        )


    def join_order_room(self, websocket: WebSocket, order_id: int) -> None:
        room = f"order:{order_id}"
        self._join_room(websocket, room)
        logger.info(f"Socket suscrito a room {room}")


    def leave_order_room(self, websocket: WebSocket, order_id: int) -> None:
        room = f"order:{order_id}"

        if room in self.rooms:
            self.rooms[room].discard(websocket)

            if websocket in self.socket_rooms:
                self.socket_rooms[websocket].discard(room)

            if not self.rooms[room]:
                del self.rooms[room]

    
    async def broadcast_to_role(self, role: str, event_type: str, data: dict[str, Any]) -> None:
        room = f"role:{role.lower()}"
        await self._emit_to_room(room, event_type, data)


    def get_active_connections_count(self) -> int:
        return len(self.socket_rooms)


    def get_rooms_info(self) -> dict[str, int]:
        return {room: len(sockets) for room, sockets in self.rooms.items()}


    def _join_room(self, websocket: WebSocket, room: str) -> None:
        if room not in self.rooms:
            self.rooms[room] = set()

        self.rooms[room].add(websocket)

        if websocket not in self.socket_rooms:
            self.socket_rooms[websocket] = set()

        self.socket_rooms[websocket].add(room)


    async def _emit_to_room(self, room: str, event_type: str, data: dict[str, Any]) -> None:
        if room not in self.rooms:
            logger.info(f"Evento {event_type} descartado (room {room} vacía).")

            return

        payload = {"event": event_type, "data": data}
        logger.info(f"Emit {event_type} a room {room} ({len(self.rooms[room])} sockets).")

        for connection in list(self.rooms[room]):
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.warning(f"Error al enviar WebSocket. Removiendo conexión: {e}")
                self.disconnect(connection)


    async def broadcast_pedido(self, pedido_id: int, dueno_id: int, evento: dict[str, Any]) -> None:
            rooms = [f"order:{pedido_id}", f"user:{dueno_id}", "role:admin", "role:pedidos"]
            logger.info(f"Broadcast {evento.get('event')} pedido={pedido_id} a {rooms}")
            await self._send_to_rooms(rooms, evento) 


manager = ConnectionManager()