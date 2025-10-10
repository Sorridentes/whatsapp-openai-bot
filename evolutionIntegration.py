from requests import Response
import requests
from config import Config
from urllib.parse import quote as format_url
from whatsappMessage import WhatsAppMessage

class EvolutionIntegration:
    def __init__(self):
        self.apikey: str = Config.EVOLUTION_APIKEY
        self.base_url: str = Config.EVOLUTION_SERVER_URL
        self.nameInstance: str = format_url(Config.EVOLUTION_NAME_INSTANCE)

    def send_message(self, whatsappMessage: WhatsAppMessage) -> bool:
        """
        Envia uma mensagem via EvolutionAPI.
        """
        url: str = f"{self.base_url}/message/sendText/{self.nameInstance}"
        payload: dict[str, str] = {
            "number": f"{whatsappMessage.to_number}",
            "text": f"{whatsappMessage.message_text}",
        }
        headers: dict[str, str] = {
            "apikey": self.apikey,
            "Content-Type": "application/json"
        }

        try:
            response: Response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            whatsappMessage.add_to_history({
                "role": "user", 
                "content": [
                    {
                        "type": "input_text", 
                        "text": whatsappMessage.message_text
                    }
                ]
            })
            whatsappMessage.add_to_history({
                "role": "user", 
                "content": [
                    {
                        "type": "text", 
                        "text": whatsappMessage.message_text
                    }
                ]
            })
            return True
        except (requests.HTTPError, requests.RequestException) as e:
            return False
        
    def webhook_response(self, data: dict) -> dict:
        """
        Processa a resposta do webhook recebido da EvolutionAPI.
        """