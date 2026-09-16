# Chatbot v1 - Frontend

Frontend Next.js + TypeScript cho chatbot v1. Tin nhắn chỉ được giữ trong state của trang và không gửi lịch sử hội thoại lên backend.

## Chạy ứng dụng

```powershell
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Mặc định frontend chạy tại `http://localhost:3000` và chuyển tiếp `/api/chat` tới `http://127.0.0.1:8000/chat`.

Nếu backend chạy ở địa chỉ khác, sửa `BACKEND_URL` trong `.env.local` rồi khởi động lại frontend.
