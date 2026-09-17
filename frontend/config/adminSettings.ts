export interface SettingPresentation {
  title: string;
  description: string;
  unit?: string;
}

export const GROUP_TITLES: Record<string, string> = {
  "Model/Quota": "Mô hình AI và hạn mức",
  "Rate Limit": "Giới hạn theo người dùng",
  Queue: "Hàng đợi và worker",
  Retry: "Thử lại khi dịch vụ lỗi",
};

export const SECRET_TITLES: Record<string, string> = {
  DATABASE_URL: "Cơ sở dữ liệu PostgreSQL",
  REDIS_URL: "Redis",
  JWT_SECRET_KEY: "Khóa ký phiên đăng nhập",
  GEMINI_API_KEY: "Khóa API Gemini",
};

export const SETTING_PRESENTATION: Record<string, SettingPresentation> = {
  DEFAULT_MODEL_NAME: {
    title: "Model trả lời mặc định",
    description: "Model dùng cho các cuộc trò chuyện thông thường.",
  },
  SUMMARY_MODEL_NAME: {
    title: "Model tóm tắt lịch sử",
    description: "Model nén hội thoại cũ thành bản tóm tắt.",
  },
  ADVANCED_MODEL_NAME: {
    title: "Model nâng cao",
    description: "Model dùng khi yêu cầu chọn chế độ nâng cao.",
  },
  DEFAULT_MODEL_RPM: {
    title: "Số lượt gọi model mặc định mỗi phút",
    description: "Hạn mức RPM do Google cấp cho model mặc định.",
    unit: "lượt/phút",
  },
  DEFAULT_MODEL_INPUT_TPM: {
    title: "Token đầu vào model mặc định mỗi phút",
    description: "Hạn mức input TPM do Google cấp cho model mặc định.",
    unit: "token/phút",
  },
  DEFAULT_MODEL_RPD: {
    title: "Số lượt gọi model mặc định mỗi ngày",
    description: "Hạn mức RPD do Google cấp cho model mặc định.",
    unit: "lượt/ngày",
  },
  SUMMARY_MODEL_RPM: {
    title: "Số lượt gọi model tóm tắt mỗi phút",
    description: "Hạn mức RPM của model tóm tắt.",
    unit: "lượt/phút",
  },
  SUMMARY_MODEL_INPUT_TPM: {
    title: "Token đầu vào model tóm tắt mỗi phút",
    description: "Hạn mức input TPM của model tóm tắt.",
    unit: "token/phút",
  },
  SUMMARY_MODEL_RPD: {
    title: "Số lượt gọi model tóm tắt mỗi ngày",
    description: "Hạn mức RPD của model tóm tắt.",
    unit: "lượt/ngày",
  },
  ADVANCED_MODEL_RPM: {
    title: "Số lượt gọi model nâng cao mỗi phút",
    description: "Hạn mức RPM của model nâng cao.",
    unit: "lượt/phút",
  },
  ADVANCED_MODEL_INPUT_TPM: {
    title: "Token đầu vào model nâng cao mỗi phút",
    description: "Hạn mức input TPM của model nâng cao.",
    unit: "token/phút",
  },
  ADVANCED_MODEL_RPD: {
    title: "Số lượt gọi model nâng cao mỗi ngày",
    description: "Hạn mức RPD của model nâng cao.",
    unit: "lượt/ngày",
  },
  SAFE_RPM_RATIO: {
    title: "Tỷ lệ an toàn cho lượt gọi mỗi phút",
    description: "Phần quota RPM được phép dùng; 0.9 tương đương 90%.",
    unit: "tỷ lệ 0–1",
  },
  SAFE_TPM_RATIO: {
    title: "Tỷ lệ an toàn cho token mỗi phút",
    description: "Phần quota TPM được phép dùng; 0.9 tương đương 90%.",
    unit: "tỷ lệ 0–1",
  },
  SAFE_RPD_RATIO: {
    title: "Tỷ lệ an toàn cho lượt gọi mỗi ngày",
    description: "Phần quota RPD được phép dùng; 0.9 tương đương 90%.",
    unit: "tỷ lệ 0–1",
  },
  FALLBACK_ENABLED: {
    title: "Tự động chuyển model dự phòng",
    description: "Chuyển về model mặc định khi model khác tạm thời không khả dụng.",
  },
  USER_RATE_CAPACITY: {
    title: "Số yêu cầu tối đa được tích lũy",
    description: "Dung lượng token bucket của mỗi người dùng.",
    unit: "yêu cầu",
  },
  USER_RATE_REFILL_TOKENS: {
    title: "Số yêu cầu được cấp lại mỗi chu kỳ",
    description: "Lượng quyền gửi được bổ sung sau mỗi chu kỳ.",
    unit: "yêu cầu",
  },
  USER_RATE_REFILL_SECONDS: {
    title: "Thời gian cấp lại quyền gửi",
    description: "Độ dài một chu kỳ refill của giới hạn người dùng.",
    unit: "giây",
  },
  MAX_ACTIVE_GENERATIONS_PER_USER: {
    title: "Số yêu cầu đang xử lý tối đa mỗi người dùng",
    description: "Giới hạn tổng job chưa kết thúc của một tài khoản.",
    unit: "job",
  },
  MAX_QUEUE_SIZE: {
    title: "Sức chứa hàng đợi tối đa",
    description: "Số job được phép tồn tại đồng thời trong hệ thống.",
    unit: "job",
  },
  MAX_QUEUE_WAIT_SECONDS: {
    title: "Thời gian chờ hàng đợi tối đa",
    description: "Job chờ lâu hơn thời gian này sẽ thất bại.",
    unit: "giây",
  },
  QUEUE_EVENT_TTL_SECONDS: {
    title: "Thời gian lưu sự kiện trạng thái",
    description: "Thời gian Redis giữ sự kiện SSE để client kết nối lại.",
    unit: "giây",
  },
  QUEUE_JOB_MAX_ATTEMPTS: {
    title: "Số lần xử lý tối đa của một job",
    description: "Giới hạn số lần worker nhận lại một job bị lỗi.",
    unit: "lần",
  },
  WORKER_CONCURRENCY: {
    title: "Số job worker xử lý song song",
    description: "Mức song song của mỗi tiến trình worker.",
    unit: "job",
  },
  WORKER_LEASE_SECONDS: {
    title: "Thời hạn giữ job của worker",
    description: "Sau thời gian này, job mất heartbeat có thể được worker khác thu hồi.",
    unit: "giây",
  },
  GEMINI_REQUEST_TIMEOUT_SECONDS: {
    title: "Thời gian chờ một lần gọi Gemini",
    description: "Hủy một provider attempt nếu Gemini phản hồi quá lâu.",
    unit: "giây",
  },
  GEMINI_MAX_RETRY_ATTEMPTS: {
    title: "Số lần gọi Gemini tối đa",
    description: "Tổng số provider attempt được phép cho một lượt xử lý.",
    unit: "lần",
  },
  GEMINI_MAX_RETRY_ELAPSED_SECONDS: {
    title: "Tổng thời gian thử lại tối đa",
    description: "Không tiếp tục retry khi vượt quá ngân sách thời gian này.",
    unit: "giây",
  },
  GEMINI_RETRY_INITIAL_DELAY_SECONDS: {
    title: "Độ trễ thử lại ban đầu",
    description: "Mốc ban đầu cho exponential backoff và jitter.",
    unit: "giây",
  },
  GEMINI_RETRY_MAX_DELAY_SECONDS: {
    title: "Độ trễ tối đa giữa hai lần thử",
    description: "Giới hạn thời gian chờ của một bước backoff.",
    unit: "giây",
  },
};

export function settingPresentation(key: string): SettingPresentation {
  return SETTING_PRESENTATION[key] ?? {
    title: key,
    description: "Cấu hình vận hành hệ thống.",
  };
}
