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
CHAT_CONTEXT_WINDOW_TOKENS=10000
SUMMARY_CONTEXT_WINDOW_TOKENS=15000
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

## Ngân sách token

`CHAT_CONTEXT_WINDOW_TOKENS` được chia theo tỷ lệ trong `.env`: input 75% và output 25%. Input gồm system 5%, câu hỏi 10%, summary 15% và recent messages tối đa 45%.

Khi recent vượt 45%, các cặp hỏi–đáp cũ được gối vào summary để recent về gần `TARGET_HISTORY_RECENT_MESSAGES_RATIO=30%`. `RECENT_MESSAGE_LIMIT` là ngưỡng an toàn phụ cho nhiều message rất ngắn. Message chỉ bị loại khỏi recent sau khi đã được gối thành công vào summary.

Model summary dùng `SUMMARY_CONTEXT_WINDOW_TOKENS` riêng. Input tối đa của mỗi lượt summary bằng context này trừ ngân sách output summary; dữ liệu lớn được chia thành nhiều batch tại ranh giới cặp hỏi–đáp.
