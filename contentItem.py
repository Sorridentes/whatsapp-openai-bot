from pydantic import BaseModel, model_validator
from typing import Optional, Literal, Any


class ContentItem(BaseModel):
    type: Literal[
        "output_text", "input_text", "input_image", "input_file", "input_audio"
    ]
    text: Optional[str] = None
    url: Optional[str] = None
    media_key: Optional[str] = None
    mimetype: Optional[str] = None
    caption: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_type_and_field(cls, values: Any):
        t = values.get("type")
        if t in ("output_text", "input_text") and not values.get("text"):
            raise ValueError(f"'text' is required for type '{t}'")
        if t in ("input_image", "input_file", "input_audio") and not values.get("url"):
            raise ValueError("'audio_url' is required for type 'input_file'")
        return values
