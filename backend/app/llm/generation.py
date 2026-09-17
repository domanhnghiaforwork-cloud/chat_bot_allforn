from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    model: str
    actual_input_tokens: int
    output_tokens: int


def estimate_tokens(text: str) -> int:
    """Ước lượng bảo thủ để kiểm tra context và reserve TPM trước provider call."""
    return max(1, (len(text) + 2) // 3)


def should_count_exactly(estimated: int, limit: int, threshold: float) -> bool:
    """Chỉ gọi tokenizer của provider khi ước lượng đã sát giới hạn."""
    return estimated >= limit * threshold
