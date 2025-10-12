from openai import OpenAI
from config import Config
from whatsappMessage import WhatsappMessage
from typing import Any
import logging

logger: logging.Logger = logging.getLogger(__name__)

class OpenaiIntegration:
    def __init__(self):
        self.client: OpenAI = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def create_response(self, WhatsappMessage: WhatsappMessage) -> Any:
        """
        Cria uma resposta utilizando o modelo da OpenAI.
        """
        try:
            response: Any = self.client.responses.create(
                prompt={
                    "id": Config.OPENAI_PROMPT_ID,
                    "version": Config.PROMPT_ID_VERSION
                },
                input=WhatsappMessage.history,
                text={
                    "format": {
                    "type": "text"
                    }
                },
                reasoning={},
                max_output_tokens=512,
                store=True
            )
        except Exception as e:
            logger.error(f"Erro ao criar responsta da OpenAI para {WhatsappMessage.to_number}: {e}")
            raise e
        else:
            logger.info(f"Resposta gerada com sucesso para {WhatsappMessage.to_number}")
            WhatsappMessage.add_to_history({
                "id": response.output[0].id,
                "role": "assistant", 
                "content": [
                    {
                        "type": "output_text", 
                        "text": response.output[0].content[0].text
                    }
                ]
            })
            return response.output[0].content[0].text
