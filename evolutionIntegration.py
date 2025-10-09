from requests import Response
import requests
from config import Config
from urllib.parse import quote as format_url

class EvolutionIntegration:
    def __init__(self):
        self.apikey: str = Config.EVOLUTION_APIKEY
        self.base_url: str = Config.EVOLUTION_SERVER_URL
        self.nameInstance: str = format_url(Config.EVOLUTION_NAME_INSTANCE)

    def send_message(self, to: str, message: str) -> dict:
        """
        Envia uma mensagem via EvolutionAPI.
        """
        url: str = f"{self.base_url}/message/sendText/{self.nameInstance}"
        payload: dict[str, str] = {
            "number": f"{to}",
            "text": f"{message}",
        }
        headers: dict[str, str] = {
            "apikey": self.apikey,
            "Content-Type": "application/json"
        }

        try:
            response: Response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            return {"error": str(e)}
        except requests.RequestException as e:
            return {"error": str(e)}
        
    def webhook_response(self, data: dict) -> dict:
        """
        Processa a resposta do webhook recebido da EvolutionAPI.
        """