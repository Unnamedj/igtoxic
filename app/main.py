import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import init_db
from app.routers.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = None
    if os.getenv("IG_USERNAME"):
        from worker.scheduler import main_loop
        task = asyncio.create_task(main_loop())
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="IGToxic Analytics", lifespan=lifespan)
app.include_router(api_router)

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))
