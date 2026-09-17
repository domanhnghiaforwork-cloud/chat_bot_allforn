# Chatbot v3 - Backend

FastAPI + PostgreSQL + Gemini, có JWT, mật khẩu Argon2 và dữ liệu hội thoại tách theo user.

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

Với database v2 đang có hội thoại, migration không tự chọn chủ sở hữu. Đặt hai biến sau trước khi chạy:

```env
V2_OWNER_EMAIL=owner@example.com
V2_OWNER_PASSWORD=your_password_at_least_8_chars
```

Tài khoản này được tạo trong migration và nhận toàn bộ hội thoại v2. Database mới không cần hai biến trên.

## API chính

- `POST /auth/register`: tạo tài khoản và trả access token.
- `POST /auth/login`: đăng nhập.
- `GET /users/me`: lấy user hiện tại.
- `/conversations` và `/chat`: yêu cầu `Authorization: Bearer <token>`.

Context Gemini vẫn theo v2: `System Prompt + Summary + Recent Messages + Current Question`, với ngân sách token cấu hình hoàn toàn qua ENV.
