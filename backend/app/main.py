from fastapi import FastAPI

from app.api.chat import router as chat_router

app = FastAPI(title="Chatbot v1")
app.include_router(chat_router)
