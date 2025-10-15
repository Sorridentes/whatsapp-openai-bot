from pydantic import BaseModel, model_validator
from typing import Optional, Literal, Any


class ContentItem(BaseModel):
    type: Literal["output_text", "input_text", "input_image", "input_file"]
    text: Optional[str] = None
    image_url: Optional[str] = None
    file_url: Optional[str] = None
    media_key: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_type_and_field(cls, values: Any):
        t = values.get("type")
        if t in ("output_text", "input_text") and not values.get("text"):
            raise ValueError(f"'text' is required for type '{t}'")
        if t == "input_image" and not values.get("image_url"):
            raise ValueError("'image_url' is required for type 'input_image'")
        if t == "input_file" and not values.get("file_url"):
            raise ValueError("'file_url' is required for type 'input_file'")
        return values
