from requests import Response
import requests
from config import Config
from urllib.parse import quote as format_url
from whatsappMessage import WhatsappMessage
from logging import Logger, getLogger

logger: Logger = getLogger(__name__)

class EvolutionIntegration:
    def __init__(self):
        self.apikey: str = Config.EVOLUTION_APIKEY
        self.base_url: str = Config.EVOLUTION_SERVER_URL
        self.nameInstance: str = format_url(Config.EVOLUTION_NAME_INSTANCE)

    def send_message(self, whatsappMessage: WhatsappMessage) -> bool:
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
            logger.info(f"Mensagem enviada com sucesso para {whatsappMessage.to_number}")
            whatsappMessage.add_to_history({
                "role": "user", 
                "content": [
                    {
                        "type": "input_text", 
                        "text": whatsappMessage.message_text
                    }
                ]
            })
            return True
        except (requests.HTTPError, requests.RequestException) as e:
            logger.error(f"Erro ao enviar mensagem para {whatsappMessage.to_number}: {e}")
            return False