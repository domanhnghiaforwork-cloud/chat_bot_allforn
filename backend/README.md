# Chatbot v4.2 - Backend

FastAPI + PostgreSQL + Redis Streams + Gemini/OpenAI Gateway, có role, quota và audit.

## Chọn nguồn mô hình bằng ENV

Sửa `backend/.env` (Docker Compose cũng đọc file này cho cả API và worker):

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_REQUEST_TIMEOUT_SECONDS=60
```

`OPENAI_MODEL` nhận ID model hỗ trợ Responses API và có quyền truy cập trong tài khoản
của bạn. Đổi ID này để thêm/sử dụng model OpenAI khác, không cần sửa mã nguồn.
Đặt `OPENAI_SUMMARY_MODEL` và `OPENAI_ADVANCED_MODEL` nếu muốn model riêng cho tóm tắt
và chế độ nâng cao; nếu không đặt, cả hai dùng `OPENAI_MODEL`.

Để quay lại Gemini, đặt `AI_PROVIDER=gemini`; các biến `GEMINI_*`, `DEFAULT_MODEL_NAME`,
`SUMMARY_MODEL_NAME`, `ADVANCED_MODEL_NAME` tiếp tục được sử dụng như trước.
Chỉ nguồn đang chọn cần API key. Cấu hình model Gemini cũ trong database không thay thế
các model `OPENAI_*`. Admin vẫn chỉ chỉnh 3 giới hạn token trên giao diện; key đặt ở backend.

Sau khi sửa ENV, khởi động lại **cả API và worker**. Khi cài trực tiếp, cập nhật dependencies
bằng `pip install -r requirements.txt`. Khi dùng Docker, chạy ở thư mục gốc dự án:

```powershell
docker compose up -d --build backend worker frontend
```

OpenAI dùng Responses API cho chat thường và streaming; dùng `/v1/responses/input_tokens`
để đếm chính xác token gần giới hạn, đồng thời ghi usage vào hệ thống hiện có.
Request dùng `store=false`; lịch sử hội thoại tiếp tục được quản lý trong database ứng dụng.
Giới hạn output bao gồm token suy luận nếu model có sử dụng chúng.

Quota OpenAI do provider kiểm soát; lỗi 429 dùng cơ chế retry hiện có. Nếu cần giới hạn
Redis bổ sung, đặt **đủ** `OPENAI_RPM`, `OPENAI_INPUT_TPM`, `OPENAI_RPD` theo tài khoản;
các giá trị này áp dụng cho từng model OpenAI. Counter tách riêng khỏi Gemini.
Các biến `GEMINI_MAX_RETRY_*`/`GEMINI_RETRY_*` hiện hữu vẫn điều khiển chính sách retry
chung; timeout OpenAI dùng `OPENAI_REQUEST_TIMEOUT_SECONDS`.

Tài liệu chính thức: [Responses API](https://developers.openai.com/api/docs/guides/text),
[Counting tokens](https://developers.openai.com/api/docs/guides/token-counting).

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
# Cấu hình tải đồng thời

API giải phóng transaction xác thực trước khi xử lý tiếp. Cấu hình runtime được cache
2 giây, cập nhật admin xóa cache của tiến trình hiện tại ngay; tiến trình khác nhận thay
đổi trong thời gian TTL. Các endpoint có session sẵn dùng lại session khi đọc cấu hình.

`DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=10`, `DB_POOL_TIMEOUT_SECONDS=10` là mặc định.
Với 2 API workers và 1 queue worker, trần pool cộng lại là 60 kết nối; cần tính lại nếu
scale thêm container. Hash/verify Argon2 chạy ngoài event loop, giới hạn hai tác vụ
đồng thời mỗi tiến trình để giữ RAM ổn định.

`WORKER_CONCURRENCY` mặc định 8. Thay giá trị cần restart worker. Quota OpenAI phải lấy
từ tài khoản/model thực tế; các trường quota Gemini không áp dụng khi `AI_PROVIDER=openai`.
Kiểm thử 20 người với câu hỏi ngắn không chứng minh 20 người có thể gửi liên tục các
context lớn mà không chạm TPM. Theo dõi queue wait, retry, 429 và token usage khi dùng thật.
