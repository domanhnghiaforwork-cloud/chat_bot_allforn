# Chatbot v2

Chatbot có lịch sử hội thoại, summary và recent messages bằng FastAPI, PostgreSQL và Google GenAI SDK.

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Tạo database PostgreSQL `chatbot`, sau đó cấu hình `.env` theo `.env.example`. URL phải dùng driver asyncpg:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/chatbot
```

Thêm API key vào `.env`:

```env
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
MAX_OUTPUT_TOKENS=1024
```

Chạy ứng dụng:

```powershell
uvicorn app.main:app --reload
```

Kiểm thử tại `http://127.0.0.1:8000/docs` hoặc:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/chat `
  -ContentType 'application/json' `
  -Body '{"conversation_id":"<uuid>","message":"Xin chào"}'
```

Tạo hội thoại trước bằng `POST /conversations`. Các bảng được tự tạo khi ứng dụng khởi động; production nên dùng Alembic.
