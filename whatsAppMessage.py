from pydantic import BaseModel
from typing import Any
import logging

logger: logging.Logger = logging.getLogger(__name__)

class WhatsappMessage(BaseModel):
    to_number: str
    message_text: str
    history: list[dict[Any, Any]] = []

    def add_to_history(self, payload: dict[str, Any]) -> None:
        if len(self.history) > 6:
            self.history.pop(0)
        
        self.history.append(payload)
        logger.info(f"Histórico atualizado")