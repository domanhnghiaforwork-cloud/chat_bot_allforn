# Chatbot Gemini v3

Chatbot Next.js + FastAPI hỗ trợ nhiều tài khoản. Mỗi user chỉ truy cập được hội thoại và message của chính mình; bộ nhớ `Summary + Recent Messages` từ v2 được giữ nguyên.

## Chạy

1. Cấu hình `backend/.env` theo `backend/.env.example`.
2. Nâng schema database:

```powershell
cd backend
alembic upgrade head
```

Nếu database v2 đã có hội thoại, đặt thêm `V2_OWNER_EMAIL` và `V2_OWNER_PASSWORD` để gán toàn bộ dữ liệu cũ cho tài khoản đó.

3. Chạy backend:

```powershell
uvicorn app.main:app --reload
```

4. Chạy frontend ở terminal khác:

```powershell
cd frontend
npm install
npm run dev
```

Mở `http://localhost:3000`, đăng ký tài khoản rồi tạo hội thoại.
