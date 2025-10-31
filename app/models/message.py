from typing import List, Optional, Literal
from pydantic import BaseModel, model_validator
from .contentItem import ContentItem
import logging

logger: logging.Logger = logging.getLogger(__name__)


class Message(BaseModel):
    id: Optional[str] = None
    role: Literal["assistant", "user"]
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
                self.content.insert(
                    0, ContentItem(type="input_text", text=default_text)
                )
                logger.warning("Texto padrão adicionado ao conteúdo da mensagem.")
        return self


if __name__ == "__main__":
    msg = Message(
        id="123",
        role="user",
        content=[ContentItem(type="input_image", url="https://exemplo.com/img.jpg")],
    )
    print(msg)
