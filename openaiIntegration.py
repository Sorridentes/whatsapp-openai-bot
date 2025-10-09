from openai import OpenAI
from config import Config
from pessoa import Pessoa

class OpenaiIntegration:
    def __init__(self):
        self.client: OpenAI = OpenAI()
    
    def create_response(self, pessoa: Pessoa) -> dict:
        """
        Cria uma resposta utilizando o modelo da OpenAI.
        """
        response = self.client.responses.create(
            prompt={
                "id": "pmpt_68e7f29b766481959bca3eb9f22311320ae1cd8e223c5382",
                "version": "2"
            },
            input=[],
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
        return response