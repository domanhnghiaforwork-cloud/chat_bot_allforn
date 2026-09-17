# Chatbot v3 - Frontend

Next.js App Router + TypeScript với trang đăng ký/đăng nhập, auth store và danh sách hội thoại riêng cho user hiện tại.

## Chạy

```powershell
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Frontend chuyển tiếp `/api/*` tới FastAPI theo `BACKEND_URL`. Access token của v3 được lưu trong local storage; cookie HttpOnly và refresh token thuộc bước hardening production tiếp theo.
