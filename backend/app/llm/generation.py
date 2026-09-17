from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    model: str
    actual_input_tokens: int
    output_tokens: int


def estimate_tokens(text: str) -> int:
    """Ước lượng bảo thủ chỉ dùng để reserve TPM trước provider call."""
    return max(1, (len(text) + 2) // 3)
