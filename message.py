from typing import List, Optional, Literal, Any
from pydantic import BaseModel, model_validator

class Message(BaseModel):
    id: Optional[str] = None
    role: Literal["assistant", "user"]
    
    class ContentItem(BaseModel):
        type: Literal["output_text", "input_text", "input_image", "input_file"]
        text: Optional[str] = None
        image_url: Optional[str] = None
        file_url: Optional[str] = None

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

    content: List[ContentItem]

    @model_validator(mode="after")
    def check_and_insert_content(self):
        types = [item.type for item in self.content]
        if any(t in ("input_image", "input_file") for t in types):
            if not self.content or self.content[0].type != "input_text":
                # Insere automaticamente o input_text adequado
                if "input_image" in types:
                    default_text = "Com base na image"
                elif "input_file" in types:
                    default_text = "Com base no arquivo"
                else:
                    default_text = ""
                self.content.insert(0, self.ContentItem(type="input_text", text=default_text))
        return self

if __name__ == "__main__":
    msg = Message(
        id="123",
        role="user",
        content=[
            Message.ContentItem(type="input_image", image_url="https://exemplo.com/img.jpg")
        ]
    )
    print(msg)