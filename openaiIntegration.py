from openai import OpenAI
from config import Config
from whatsappMessage import WhatsAppMessage
from flask import HTTPException

class OpenaiIntegration:
    def __init__(self):
        self.client: OpenAI = OpenAI()
    
    def create_response(self, whatsappMessage: WhatsAppMessage) -> dict:
        """
        Cria uma resposta utilizando o modelo da OpenAI.
        """
        try:
            response = self.client.responses.create(
                prompt={
                    "id": "pmpt_68e7f29b766481959bca3eb9f22311320ae1cd8e223c5382",
                    "version": "2"
                },
                input=whatsappMessage.history,
                text={
                    "format": {
                    "type": "text"
                    }
                },
                reasoning={},
                max_output_tokens=2048,
                store=True,
                include=["web_search_call.action.sources"]
            )
            whatsappMessage.add_to_history(response.output[0])
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail="Erro ao gerar resposta da IA")