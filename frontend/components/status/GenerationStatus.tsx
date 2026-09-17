import type { GenerationStatus as Status } from "../../types/generation";

const LABELS: Partial<Record<Status, string>> = {
  PENDING: "Đang tiếp nhận yêu cầu...",
  QUEUED: "Yêu cầu đang chờ xử lý.",
  GENERATING: "AI đang tạo câu trả lời...",
  RETRYING: "Dịch vụ AI đang bận, hệ thống sẽ tự thử lại.",
  FAILED: "Yêu cầu không hoàn thành.",
  CANCELLED: "Yêu cầu đã hủy.",
};

export default function GenerationStatus({
  status,
  queuePosition,
  error,
  onCancel,
}: {
  status: Status | null;
  queuePosition: number | null;
  error: string;
  onCancel: () => void;
}) {
  if (!status || status === "DONE") return null;
  const active = ["PENDING", "QUEUED", "GENERATING", "RETRYING"].includes(status);
  return (
    <div className={`generation-status status-${status.toLowerCase()}`} role="status">
      <span>
        {error || LABELS[status]}
        {status === "QUEUED" && queuePosition ? ` Vị trí ước tính: ${queuePosition}.` : ""}
      </span>
      {active && <button type="button" onClick={onCancel}>Hủy</button>}
    </div>
  );
}
