from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ClientErrorCreate(BaseModel):
    app_version: str = Field(min_length=1, max_length=32, pattern=r"^[0-9A-Za-z.+_-]+$")
    error_type: str = Field(min_length=1, max_length=100, pattern=r"^[0-9A-Za-z.$_-]+$")
    fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    stack_frames: list[str] = Field(default_factory=list, max_length=20)
    screen: str | None = Field(default=None, max_length=50, pattern=r"^[0-9A-Za-z_.$-]+$")
    occurred_at: datetime

    @field_validator("stack_frames")
    @classmethod
    def sanitize_frames(cls, values: list[str]) -> list[str]:
        sanitized: list[str] = []
        for value in values:
            frame = value.strip()
            if len(frame) > 200 or not frame.startswith("com.flsndez.contabpareja"):
                raise ValueError(
                    "Los frames deben pertenecer a la aplicación y tener 200 caracteres."
                )
            sanitized.append(frame)
        return sanitized


class DiagnosticAccepted(BaseModel):
    accepted: bool = True
