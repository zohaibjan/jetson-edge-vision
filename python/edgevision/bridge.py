"""Single-process local bridge. Never connects a browser directly to native ZMQ."""
import asyncio
from contextlib import asynccontextmanager, suppress
import os
from pathlib import Path
from urllib.parse import urlsplit
import zmq
import zmq.asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .schema import FrameEvent

TOPIC = b"edge.detections.v1"
MAX_BYTES = 262144

class Hub:
    def __init__(self):
        self.clients: set[asyncio.Queue] = set()
        self.accepted = self.rejected = self.dropped = 0
        self.last: dict | None = None

    def ingest(self, parts: list[bytes]) -> bool:
        if len(parts) != 2 or parts[0] != TOPIC or len(parts[1]) > MAX_BYTES:
            self.rejected += 1
            return False
        try:
            event = FrameEvent.model_validate_json(parts[1]).model_dump(by_alias=True)
        except (ValidationError, ValueError):
            self.rejected += 1
            return False
        self.accepted += 1
        self.last = event
        for queue in tuple(self.clients):
            if queue.full():
                queue.get_nowait()
                self.dropped += 1
            queue.put_nowait(event)
        return True

async def subscribe(endpoint: str, hub: Hub, context=None):
    owned_context = context is None
    context = context or zmq.asyncio.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.RCVHWM, 32)
    socket.setsockopt(zmq.MAXMSGSIZE, MAX_BYTES)
    socket.setsockopt(zmq.SUBSCRIBE, TOPIC)
    socket.setsockopt(zmq.LINGER, 0)
    socket.connect(endpoint)
    try:
        while True:
            hub.ingest(await socket.recv_multipart())
    finally:
        socket.close()
        if owned_context:
            context.term()

def create_app(endpoint: str | None = None) -> FastAPI:
    hub = Hub()
    endpoint = endpoint or os.getenv("EDGE_ZMQ_ENDPOINT", "tcp://127.0.0.1:5556")
    if not endpoint.startswith("tcp://"):
        raise ValueError("Use a trusted tcp:// producer endpoint")

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(subscribe(endpoint, hub))
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    app = FastAPI(title="Jetson Edge Vision", lifespan=lifespan)
    app.state.hub = hub
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])
    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/")
    def home():
        return FileResponse(static / "index.html")

    @app.get("/health")
    def health():
        return {"status": "ok", "events": hub.accepted, "rejected": hub.rejected,
                "client_queue_drops": hub.dropped, "clients": len(hub.clients),
                "last_frame": hub.last["frame_id"] if hub.last else None}

    @app.websocket("/ws")
    async def events(websocket: WebSocket):
        origin = websocket.headers.get("origin")
        if origin and urlsplit(origin).netloc != websocket.headers.get("host"):
            await websocket.close(code=1008)
            return
        if len(hub.clients) >= 16:
            await websocket.close(code=1013)
            return
        await websocket.accept()
        queue = asyncio.Queue(maxsize=2)
        hub.clients.add(queue)
        if hub.last:
            queue.put_nowait(hub.last)
        async def send():
            while True:
                event = await queue.get()
                await asyncio.wait_for(websocket.send_json(event), timeout=5)
        async def receive():
            while True:
                await websocket.receive_text()
        sender = asyncio.create_task(send())
        receiver = asyncio.create_task(receive())
        try:
            done, _ = await asyncio.wait([sender, receiver], return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
            pass
        finally:
            hub.clients.discard(queue)
            for task in (sender, receiver):
                task.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)
    return app

app = create_app()
