# Chatbot v1

Chatbot một lượt dùng FastAPI và Google GenAI SDK chính thức. Phiên bản này không lưu lịch sử hội thoại.

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Thêm API key vào `.env`:

```env
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
MAX_OUTPUT_TOKENS=1024
```

Chạy ứng dụng:

```powershell
uvicorn app.main:app --reload
```

Kiểm thử tại `http://127.0.0.1:8000/docs` hoặc:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/chat `
  -ContentType 'application/json' `
  -Body '{"message":"Xin chào"}'
```
