# Deploy chatbot v4.2 bằng Docker Compose

Bộ Compose chạy 5 thành phần độc lập: frontend, backend API, worker, PostgreSQL và
Redis. Migration Alembic chạy tự động trước khi API/worker khởi động.

## 1. Chuẩn bị cấu hình

Tại thư mục gốc dự án:

```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
```

Sửa hai file vừa tạo:

- `.env`: đổi `POSTGRES_PASSWORD` thành chuỗi dài, ngẫu nhiên, URL-safe. Điều
  chỉnh `APP_PORT` và `API_WORKERS` nếu cần.
- `backend/.env`: đặt `GEMINI_API_KEY`, tạo `JWT_SECRET_KEY` tối thiểu 32 ký tự,
  kiểm tra model và quota thực tế. `DATABASE_URL` và `REDIS_URL` trong file này
  được Compose tự ghi đè bằng địa chỉ nội bộ container.
- Không commit hai file `.env`; chúng đã được ignore và không được copy vào image.

Nếu muốn chạy flow đồng bộ cũ, đặt cả `ASYNC_CHAT_ENABLED=false` và
`QUEUE_ENABLED=false` trong `.env`. Giá trị async của frontend được đóng vào lúc
build, nên cần build lại frontend khi đổi cờ này.

## 2. Build và chạy

```powershell
docker compose config --quiet
docker compose build --pull
docker compose up -d
docker compose ps
```

Mở `http://localhost:3000` (hoặc cổng `APP_PORT`). Kiểm tra toàn bộ đường đi
frontend -> backend -> PostgreSQL/Redis:

```powershell
Invoke-RestMethod http://localhost:3000/api/health/ready
docker compose logs --tail=100 backend worker frontend
```

Kết quả readiness hợp lệ có `status=ready`, `postgres=true`, `redis=true`.

## 3. Vận hành

Xem log liên tục:

```powershell
docker compose logs -f --tail=200 backend worker
```

Tạo admin đầu tiên:

```powershell
docker compose exec backend python -m app.cli promote-admin admin@example.com --reason "Khởi tạo quản trị viên"
```

Nếu tải tăng, có thể tăng số worker xử lý queue mà không rebuild image:

```powershell
docker compose up -d --scale worker=2
```

Quota model vẫn được điều phối tập trung qua Redis; theo dõi database connections,
CPU và RAM trước khi tăng `API_WORKERS` hoặc `WORKER_CONCURRENCY`.

Cập nhật phiên bản:

```powershell
git pull
docker compose build --pull
docker compose up -d
docker compose ps
```

Alembic sẽ chạy lại an toàn khi image thay đổi. Dừng dịch vụ nhưng giữ dữ liệu:

```powershell
docker compose down
```

Không dùng `docker compose down -v` trên production vì tùy chọn `-v` xóa volume
PostgreSQL và Redis.

# Tắt
docker compose stop

# Bật
docker compose up -d

# Sửa code rồi chạy lại
docker compose up -d --build

## 4. Ghi chú production

- Chỉ cổng frontend được publish; backend, PostgreSQL và Redis chỉ nằm trong mạng
  nội bộ Compose.
- Đặt reverse proxy/load balancer có HTTPS trước cổng frontend khi public Internet.
- Sao lưu volume PostgreSQL định kỳ. Redis đã bật AOF `everysec` để bảo vệ queue,
  nhưng không thay thế backup.
- Image frontend dùng Next.js standalone; image backend chỉ chứa virtualenv và mã
  runtime. Cả hai tiến trình ứng dụng chạy bằng user không phải root.
- `backend/.env` phù hợp cho một máy chủ. Với nền tảng orchestration, nên đưa
  secret qua secret manager của nền tảng thay vì lưu file trên máy.
