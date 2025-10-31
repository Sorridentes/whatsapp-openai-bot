from requests import Response
import requests
from urllib.parse import quote as format_url
from logging import Logger, getLogger

from app.core.config import Config
from app.models.whatsappMessage import WhatsappMessage

logger: Logger = getLogger(__name__)


class EvolutionIntegration:
    def __init__(self):
        self.apikey: str = Config.EVOLUTION_APIKEY
        self.base_url: str = Config.EVOLUTION_SERVER_URL
        self.nameInstance: str = format_url(Config.EVOLUTION_NAME_INSTANCE)

    def send_message(self, whatsappMessage: WhatsappMessage) -> None:
        """
        Envia uma mensagem via EvolutionAPI.
        """
        url: str = f"{self.base_url}/message/sendText/{self.nameInstance}"
        payload: dict[str, str] = {
            "number": f"{whatsappMessage.to_number}",
            "text": f"{whatsappMessage.message.content[0].text}",
        }
        headers: dict[str, str] = {
            "apikey": self.apikey,
            "Content-Type": "application/json",
        }

        try:
            response: Response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except (requests.HTTPError, requests.RequestException) as e:
            logger.error(
                f"Erro ao enviar mensagem para {whatsappMessage.to_number}",
                exc_info=True,
            )
            raise e
        else:
            logger.info(
                f"Mensagem enviada com sucesso para {whatsappMessage.to_number}"
            )
