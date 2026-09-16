# Chatbot v2 - Frontend

Frontend Next.js + TypeScript cho chatbot v2. Sidebar quản lý các hội thoại; route `/chat/[conversationId]` tải lại message đã lưu trong PostgreSQL.

## Chạy ứng dụng

```powershell
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Mặc định frontend chạy tại `http://localhost:3000` và chuyển tiếp `/api/*` tới FastAPI tại `http://127.0.0.1:8000/*`.

Nếu backend chạy ở địa chỉ khác, sửa `BACKEND_URL` trong `.env.local` rồi khởi động lại frontend.
