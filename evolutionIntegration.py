from requests import Response
import requests
from config import Config
from urllib.parse import quote as format_url

class EvolutionIntegration:
    def __init__(self):
        self.apikey: str = Config.APIKEY
        self.base_url: str = Config.SERVER_URL
        self.nameInstance: str = format_url(Config.NAME_INSTANCE)

    def send_message(self, to: str, message: str) -> dict:
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
        try:
            message_type: str = data.get("type")
            if message_type != "text":
                return {"error": "Unsupported message type"}

            from_number: str = data.get("from", "")
            message_text: str = data.get("body", "")

            return {
                "from": from_number,
                "message": message_text
            }
        except Exception as e:
            return {"error": str(e)}