from message import Message
from pydantic import BaseModel
from typing import Any
import logging

logger: logging.Logger = logging.getLogger(__name__)

class WhatsappMessage(BaseModel):
    to_number: str
    message: Message
    history: list[Any] = []

    def add_to_history(self) -> None:
        if len(self.history) > 6:
            self.history.pop(0)
        
        self.history.append(self.message.model_dump(exclude_none=True))
        logger.info(f"Histórico atualizado")
