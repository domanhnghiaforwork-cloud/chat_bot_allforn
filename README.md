# Chatbot Gemini v2

Chatbot Next.js + FastAPI có lịch sử hội thoại trong PostgreSQL. Context gửi Gemini gồm `System Prompt + Summary + Recent Messages + Current Question`.

Chat và summary có context riêng qua `CHAT_CONTEXT_WINDOW_TOKENS` và `SUMMARY_CONTEXT_WINDOW_TOKENS`. Khi recent vượt 45% context chat, các cặp hỏi–đáp cũ được gối vào summary để recent về gần 30%; giới hạn 200 message là lớp an toàn phụ.

## Chạy

1. Tạo PostgreSQL database `chatbot` và thêm `DATABASE_URL` vào `backend/.env` theo `backend/.env.example`.
2. Chạy backend:

```powershell
cd backend
..\..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

3. Chạy frontend ở terminal khác:

```powershell
cd frontend
npm install
npm run dev
```

Mở `http://localhost:3000`.
