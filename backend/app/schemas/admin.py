from typing import Any

from pydantic import BaseModel, Field, model_validator


class SettingUpdate(BaseModel):
    value: Any
    reason: str = Field(min_length=3, max_length=500)


class SettingDelete(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class SettingChange(BaseModel):
    key: str = Field(min_length=1, max_length=96)
    value: Any = None
    reset: bool = False


class SettingsBatchUpdate(BaseModel):
    changes: list[SettingChange] = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def unique_keys(self) -> "SettingsBatchUpdate":
        keys = [change.key for change in self.changes]
        if len(keys) != len(set(keys)):
            raise ValueError("Mỗi cấu hình chỉ được xuất hiện một lần")
        return self
