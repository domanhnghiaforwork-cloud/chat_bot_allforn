from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.db.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Chatbot v2", lifespan=lifespan)
app.include_router(chat_router)
app.include_router(conversations_router)
