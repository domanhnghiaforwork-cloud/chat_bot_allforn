from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.users import router as users_router

app = FastAPI(title="Chatbot v3")
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(chat_router)
app.include_router(conversations_router)
