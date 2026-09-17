# Chatbot v4.2 - Frontend

Next.js App Router + TypeScript với dual sync/async flow, trạng thái job và dashboard admin.

## Chạy

```powershell
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Frontend chuyển tiếp `/api/*` tới FastAPI theo `BACKEND_URL`. Access token của v3 được lưu trong local storage; cookie HttpOnly và refresh token thuộc bước hardening production tiếp theo.

`NEXT_PUBLIC_ASYNC_CHAT_ENABLED=false` giữ flow `/chat` cũ; chỉ bật `true` sau khi
Redis, worker, `QUEUE_ENABLED` và `ASYNC_CHAT_ENABLED` ở backend đã sẵn sàng.
