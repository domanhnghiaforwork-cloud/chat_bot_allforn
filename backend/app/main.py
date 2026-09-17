from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.generations import router as generations_router
from app.api.users import router as users_router
from app.db.database import engine
from app.redis_client import close_redis_clients, redis_ready


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_redis_clients()
    await engine.dispose()


app = FastAPI(title="Chatbot v4.2", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(generations_router)
app.include_router(admin_router)


@app.get("/health/live", include_in_schema=False)
async def live():
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
async def ready():
    postgres_ok = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        pass
    redis_ok = await redis_ready()
    payload = {"status": "ready" if postgres_ok and redis_ok else "not_ready", "postgres": postgres_ok, "redis": redis_ok}
    return JSONResponse(payload, status_code=200 if postgres_ok and redis_ok else 503)
