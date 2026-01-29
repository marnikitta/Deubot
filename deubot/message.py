from dataclasses import dataclass


@dataclass
class UserMessage:
    text: str | None = None
    image_base64: str | None = None  # JPEG base64-encoded
