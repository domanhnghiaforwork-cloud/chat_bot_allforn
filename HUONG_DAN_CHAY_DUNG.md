# Hướng dẫn chạy và dừng hệ thống

Tài liệu này dùng cho môi trường local Windows/PowerShell.

## 1. Chạy hệ thống

Chạy đúng thứ tự dưới đây. Mỗi thành phần nên dùng một terminal riêng.

### Terminal 1 - Redis

```powershell
docker start chatbot-redis
docker exec chatbot-redis redis-cli PING
```

Kết quả hợp lệ: `PONG`.

### Terminal 2 - Backend API

```powershell
cd D:\nghia\chat_bot_gemini\chat_bot_allforn\backend
..\..\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Kiểm tra backend:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

`health/ready` phải báo `postgres=true` và `redis=true`.

### Terminal 3 - Worker

```powershell
cd D:\nghia\chat_bot_gemini\chat_bot_allforn\backend
..\..\.venv\Scripts\Activate.ps1
python -m app.queue.worker
```

Không đóng terminal này khi đang dùng chat async.

### Terminal 4 - Frontend

```powershell
cd D:\nghia\chat_bot_gemini\chat_bot_allforn\frontend
npm run dev
```

Mở: http://localhost:3000

## 2. Dừng hệ thống

Dừng theo thứ tự ngược lại:

1. Terminal frontend: nhấn `Ctrl+C`.
2. Terminal worker: nhấn `Ctrl+C`.
3. Terminal backend: nhấn `Ctrl+C`.
4. Dừng Redis nếu không còn sử dụng:

```powershell
docker stop chatbot-redis
```

Không cần xóa container hoặc volume Redis. Dữ liệu queue/AOF nằm trong volume
`chatbot-redis-data` và sẽ được dùng lại ở lần chạy sau.

## 3. Khi bị mất terminal

Tìm process backend theo cổng `8000`:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  Select-Object LocalPort, OwningProcess
```

Tìm process frontend theo cổng `3000`:

```powershell
Get-NetTCPConnection -LocalPort 3000 -State Listen |
  Select-Object LocalPort, OwningProcess
```

Tìm worker:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like '*app.queue.worker*' } |
  Select-Object ProcessId, CommandLine
```

Sau khi kiểm tra đúng PID, dừng process tương ứng:

```powershell
Stop-Process -Id <PID>
```

## 4. Kiểm tra nhanh trạng thái

```powershell
docker ps --filter "name=chatbot-redis"
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Get-NetTCPConnection -LocalPort 3000 -State Listen
```

