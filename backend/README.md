# Chatbot v4.2 - Backend

FastAPI + PostgreSQL + Redis Streams + Gemini Gateway, có role, quota và audit.

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Tạo `.env` theo `.env.example`, sau đó chạy migration và ứng dụng:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

Worker async chạy bằng tiến trình riêng:

```powershell
python -m app.queue.worker
```

Gán admin đầu tiên bằng CLI có audit (không có API tự nâng quyền):

```powershell
python -m app.cli promote-admin admin@example.com --reason "Khởi tạo quản trị viên"
```

Với database v2 đang có hội thoại, migration không tự chọn chủ sở hữu. Đặt hai biến sau trước khi chạy:

```env
V2_OWNER_EMAIL=owner@example.com
V2_OWNER_PASSWORD=your_password_at_least_8_chars
```

Tài khoản này được tạo trong migration và nhận toàn bộ hội thoại v2. Database mới không cần hai biến trên.

## API chính

- `POST /auth/register`: tạo tài khoản và trả access token.
- `POST /auth/login`: đăng nhập.
- `GET /users/me`: lấy user hiện tại kèm role.
- `POST /chat`: contract đồng bộ tương thích v3.
- `POST /chat/jobs` và `/generations/*`: queue/status/SSE/cancel.
- `/admin/*`: chỉ role=admin; setting thay đổi được ghi audit.

Context Gemini vẫn theo v2: `System Prompt + Summary + Recent Messages + Current Question`, với ngân sách token cấu hình hoàn toàn qua ENV.
