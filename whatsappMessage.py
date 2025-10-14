from message import Message
from pydantic import BaseModel
from typing import Any
import logging

logger: logging.Logger = logging.getLogger(__name__)


class WhatsappMessage(BaseModel):
    to_number: str
    message: Message
    history_to_DB: list[Any] = []
    history_to_AI: list[Any] = []

    def add_to_history_DB(self) -> None:
        if len(self.history_to_DB) > 6:
            self.history_to_DB.pop(0)

        self.history_to_DB.append(self.message.model_dump(exclude_none=True))
        logger.info(f"Histórico para database atualizado")

    def add_to_history_AI(self, message: Message) -> None:
        if len(self.history_to_AI) > 6:
            self.history_to_AI.pop(0)

        self.history_to_AI.append(message.model_dump(exclude_none=True))
        logger.info(f"Histórico para AI atualizado")
