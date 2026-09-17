from typing import Any

from google.genai import types


async def count_tokens(
    client: Any,
    model: str,
    contents: Any,
    system_instruction: str | None = None,
) -> int:
    """Dùng tokenizer của đúng model thay vì ước lượng theo số ký tự."""
    # Developer API chưa nhận system_instruction trong CountTokensConfig,
    # nên ghép nó vào nội dung tạm chỉ phục vụ phép đếm.
    counted_contents = contents
    if system_instruction:
        content_items = contents if isinstance(contents, list) else [contents]
        counted_contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=system_instruction)],
            ),
            *content_items,
        ]
    response = await client.models.count_tokens(model=model, contents=counted_contents)
    return response.total_tokens or 0
