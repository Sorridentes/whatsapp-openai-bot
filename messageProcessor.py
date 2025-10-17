import logging
import asyncio
from typing import Any, Literal, Optional, overload
from database import redis_queue, mongo_db
from whatsappMessage import WhatsappMessage
from message import Message
from contentItem import ContentItem
from openaiIntegration import clientAI
from decrypt import decryptByLink
from config import Config
import base64

logger: logging.Logger = logging.getLogger(__name__)
ACCEPTABLE_TYPES = Literal[
    "conversation", "audioMessage", "imageMessage", "documentMessage"
]

class MessageProcessor:
    @overload
    async def _process_single_message_content( self,
        type: Literal["conversation"], msg_data: dict[str, Any]
    ) -> list[ContentItem]: ...

    @overload
    async def _process_single_message_content(self,
        type: Literal["audioMessage"], msg_data: dict[str, Any]
    ) -> list[ContentItem]: ...


    @overload
    async def _process_single_message_content(self,
        type: Literal["imageMessage"], msg_data: dict[str, Any]
    ) -> list[ContentItem]: ...


    @overload
    async def _process_single_message_content(self,
        type: Literal["documentMessage"], msg_data: dict[str, Any]
    ) -> list[ContentItem]: ...

    async def process_input(self, type: ACCEPTABLE_TYPES, phone_number:str, messageInput: dict[str, Any]) -> Message:
        """Processa TODAS as mensagens pendentes de um telefone de uma vez"""
        try:
            # Aguarda o timeout para agrupar mensagens
            await asyncio.sleep(Config.BATCH_PROCESSING_DELAY)

            # Recupera todas as mensagens pendentes
            pending_messages = redis_queue.get_pending_messages(phone_number)

            if not pending_messages:
                logger.info(f"Nenhuma mensagem pendente para {phone_number}")
                pass

            logger.info(
                f"Processando {len(pending_messages)} mensagens em lote para {phone_number}"
            )

            # Processa TODAS as mensagens juntas
            await self._process_message_batch(phone_number, pending_messages)

        except Exception as e:
            logger.error(
                f"Erro ao processar mensagens em lote para {phone_number}: {str(e)}"
            )

    async def _process_message_batch(
        self, phone_number: str, messages_data: list[dict[str, Any]]
    ):
        """Processa um lote completo de mensagens e gera UMA resposta"""
        try:
            # Carrega histórico completo do MongoDB
            historical_messages = mongo_db.get_conversation_history(
                phone_number, limit=50
            )

            # Prepara o histórico combinado (histórico + novas mensagens)
            all_messages = historical_messages.copy()

            # Processa e adiciona as novas mensagens
            for msg_data in messages_data:
                processed_message = await self._process_single_message_content(msg_data)
                if processed_message:
                    all_messages.append(processed_message)

            if not all_messages:
                logger.warning(
                    f"Nenhuma mensagem válida para processar para {phone_number}"
                )
                return

            # Cria objeto WhatsappMessage com TODO o histórico
            zap_message = WhatsappMessage(
                to_number=phone_number,
                message=Message(**all_messages[-1]),  # Última mensagem como base
            )

            # Substitui o histórico pelo completo
            zap_message.history_to_DB = all_messages

            # Gera UMA resposta da OpenAI para todo o contexto
            clientAI.create_response(zap_message)

            # Salva TODAS as mensagens no MongoDB
            for msg_data in messages_data:
                mongo_db.save_conversation(phone_number, msg_data["message"])

            # Salva também a resposta no histórico
            mongo_db.save_conversation(
                phone_number, zap_message.message.model_dump(exclude_none=True)
            )

            logger.info(f"Processamento em lote concluído para {phone_number}")

        except Exception as e:
            logger.error(f"Erro no processamento em lote: {str(e)}")

    async def _process_single_message_content(
            self, type: ACCEPTABLE_TYPES, msg_data: dict[str, Any]
        ) -> list[ContentItem]:
            """Processa o conteúdo de uma única mensagem (especialmente mídias)"""
            logger.info(f"Tipo da messagem recebida: {type}")

            try:
                message_data: Any = msg_data["data"]["message"].get(type, "")
                if type == "conversation":
                    # Mensagem de texto simples
                    return [ContentItem(type="input_text", text=message_data)]
                else:
                    # Extrai informações da mídia
                    media_url: Optional[str] = message_data.get("url")
                    media_key: bytes = base64.b64decode(message_data.get("mediaKey", b""))
                    mimetype: Optional[str] = message_data.get("mimetype")
                    caption: Optional[str] = message_data.get("caption")

                    if media_url and media_key:
                        try:
                            # Determina o tipo da mídia para o decrypt
                            if type == "audioMessage":
                                media_type = "audio"
                            elif type == "imageMessage":
                                if mimetype:
                                    media_type = mimetype
                                else:
                                    media_type = "image"
                            else:
                                media_type = "document"

                            # Descriptografa e obtém URL pública
                            try:
                                public_url: str = decryptByLink(
                                    link=media_url, mediaKey=media_key, mediaType=media_type
                                )
                            except Exception as e:
                                raise e
                            
                            logger.info(
                                f"Mídia descriptografada e disponível em : {public_url}"
                            )

                            # Adiciona o item de conteúdo apropriado
                            content_items: list[ContentItem] = []
                            if type == "imageMessage":
                                # Se houver caption, adiciona como texto também
                                if caption:
                                    content_items.append(
                                        ContentItem(type="input_text", text=caption)
                                    )

                                content_items.append(
                                    ContentItem(type="input_image", image_url=public_url)
                                )
                                return content_items

                            elif type == "audioMessage":
                                # Transforma o audio em texto
                                text_of_audio: str = clientAI.transcribe_audio(public_url)
                                return [ContentItem(type="input_text", text=text_of_audio)]

                            elif type == "documentMessage":
                                if caption:
                                    content_items.append(
                                        ContentItem(type="input_text", text=caption)
                                    )

                                content_items.append(
                                    ContentItem(type="input_file", file_url=public_url)
                                )
                                return content_items
                        except Exception as e:
                            logger.error(f"Erro ao processar mídia: {e}")
                            raise e
                    raise Exception("Não foi enviado o midiaKey ou a url da mídia")

            except Exception as e:
                logger.error(f"Erro geral no process_input: {e}")
                raise e
            

# Instância global
message_processor = MessageProcessor()
