from pydantic import BaseModel

class WhatsAppMessage(BaseModel):
    to_number: str
    message_text: str
    history: list[dict] = []
    is_authorized: bool
    instance: str

    def add_to_history(self, payload: dict):
        if len(self.history) > 6:
            self.history.pop(0)
        
        self.history.append(payload)