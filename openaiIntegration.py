from typing import Any
from config import Config
from openai import OpenAI
import logging
from contentItem import ContentItem
from message import Message
from whatsappMessage import WhatsappMessage

logger: logging.Logger = logging.getLogger(__name__)


class OpenaiIntegration:
    def __init__(self):
        self.client: OpenAI = OpenAI(api_key=Config.OPENAI_API_KEY)

    def create_response(self, zapMessage: WhatsappMessage) -> None:
        """
        Cria uma resposta utilizando o modelo da OpenAI.
        Agora suporta múltiplos tipos de conteúdo.
        """
        try:
            # Prepara o input para a OpenAI baseado no histórico
            input_data: Any = zapMessage.history_to_DB
            print(input_data)

            response: Any = self.client.responses.create(
                prompt={
                    "id": Config.OPENAI_PROMPT_ID,
                    "version": Config.PROMPT_ID_VERSION,
                },
                input=input_data,
                text={"format": {"type": "text"}},
                reasoning={},
                max_output_tokens=512,
                store=True,
            )
        except Exception as e:
            logger.error(f"Erro ao criar resposta da OpenAI", exc_info=True)
            raise e
        else:
            # Atualiza a mensagem com a resposta da OpenAI
            zapMessage.message = Message(
                role="assistant",
                content=[
                    ContentItem(
                        type="output_text", text=response.output[0].content[0].text
                    )
                ],
            )
            logger.info(f"Resposta gerada com sucesso")

    def transcribe_audio(self, audio_url: str) -> str:
        """
        Usa OpenAI para transcrever áudio para texto
        """
        logger.info(f"Iniciando transcrição do áudio: {audio_url}")
        try:
            with open(audio_url, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio_file,
                    response_format="text",
                )
            logger.info(f"Transcrição concluída: {len(transcript)} caracteres")
            return transcript
        except Exception as e:
            logger.error(f"Erro na transcrição OpenAI: {str(e)}")
            raise e

# Instâncias globais
clientAI: OpenaiIntegration = OpenaiIntegration()
