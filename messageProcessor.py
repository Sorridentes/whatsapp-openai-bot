import logging
import asyncio
from typing import Any, Literal, Optional, overload
from database import redis_queue, mongo_db
from whatsappMessage import WhatsappMessage
from openaiIntegration import clientAI
from evolutionIntegration import clientEvolution
from message import Message
from contentItem import ContentItem
from openaiIntegration import clientAI
from decrypt import decryptByLink
from config import Config
import base64

logger: logging.Logger = logging.getLogger(__name__)
ACCEPTABLE_TYPES_MESSAGE = Literal[
    "conversation", "audioMessage", "imageMessage", "documentMessage"
]
ACCEPTABLE_TYPES_CONTENT = Literal[
    "output_text", "input_text", "input_image", "input_file"
]


class MessageProcessor:
    def __init__(self) -> None:
        self.message: Message = Message(role="user", content=[])
        self.zap_message: WhatsappMessage

    async def process_phone_messages(
        self, type: ACCEPTABLE_TYPES_MESSAGE, phone_number: str
    ):
        """Processa TODAS as mensagens pendentes de um telefone de uma vez"""
        try:
            # Aguarda o timeout para agrupar mensagens
            await asyncio.sleep(Config.BATCH_PROCESSING_DELAY)

            # Recupera todas as mensagens pendentes
            pending_content: list[ContentItem] = self._content_overflow(
                redis_queue.get_pending_messages(phone_number)
            )

            if not pending_content:
                logger.info(f"Nenhuma mensagem pendente para {phone_number}")
                pass

            logger.info(
                f"Processando {len(pending_content)} mensagens em lote para {phone_number}"
            )

            self.message.content = pending_content
            mongo_db.save(
                phone_number=phone_number,
                message_data=self.message.model_dump(exclude_none=True),
            )

            self.zap_message = WhatsappMessage(
                to_number=phone_number, message=self.message
            )
            try:
                # Processa TODAS as mensagens juntas
                await self._process_message_batch(phone_number)
            except TypeError as e:
                raise e

        except Exception as e:
            logger.error(
                f"Erro ao processar mensagens em lote para {phone_number}: {str(e)}"
            )
            raise e

    def _content_overflow(
        self, content_data: list[dict[str, Any]]
    ) -> list[ContentItem]:
        logger.info(f"Transbondo dados para uma lista de ContentItem")
        lst_content: list[ContentItem] = []
        for content in content_data:
            content_type: ACCEPTABLE_TYPES_CONTENT = content.get("type", "unknow")
            item_content: ContentItem = ContentItem(
                type=content_type,
                media_key=(
                    content["media_key"]
                    if content_type in ("input_file", "input_image")
                    else None
                ),
            )
            if content_type == "input_text":
                item_content.text = content["text"]
            else:
                item_content.url = content["url"]
            lst_content.append(item_content)

        return lst_content

    async def _process_message_batch(self, phone_number: str):
        """Processa um lote completo de mensagens e gera UMA resposta"""
        try:
            # Carrega histórico completo do MongoDB
            try:
                historical_messages = mongo_db.get_history(phone_number, limit=50)
            except Exception as e:
                raise e

            # Prepara o histórico combinado (histórico + novas mensagens)
            all_messages: list[dict[str, Any]] = []

            # Processa o histórico (cada document do MongoDB tem uma lista 'content')
            for hist_msg in historical_messages:
                for content_dict in hist_msg.get("content", []):
                    try:
                        processed = await self._process_single_message_content(
                            type=content_dict["type"], msg_data=content_dict
                        )
                        if processed:
                            all_messages.extend(processed)
                    except Exception as e:
                        logger.warning(f"Falha ao processar item do histórico: {e}")
                        continue

            if not all_messages:
                logger.warning(
                    f"Nenhuma mensagem válida para processar para {phone_number}"
                )

            # Substitui o histórico pelo completo
            self.zap_message.history_to_AI = all_messages

            # Gera UMA resposta da OpenAI para todo o contexto
            clientAI.create_response(self.zap_message)

            # Envia UMA resposta via Evolution
            clientEvolution.send_message(self.zap_message)

            # Salva a mensagens no MongoDB
            mongo_db.save(
                phone_number, self.zap_message.message.model_dump(exclude_none=True)
            )

            logger.info(f"Processamento em lote concluído para {phone_number}")

        except Exception as e:
            logger.error(f"Erro no processamento em lote: {str(e)}")
            raise e

    @overload
    async def _process_single_message_content(
        self, type: Literal["conversation"], msg_data: dict[str, Any]
    ) -> list[dict[str, Any]]: ...

    @overload
    async def _process_single_message_content(
        self, type: Literal["audioMessage"], msg_data: dict[str, Any]
    ) -> list[dict[str, Any]]: ...

    @overload
    async def _process_single_message_content(
        self, type: Literal["imageMessage"], msg_data: dict[str, Any]
    ) -> list[dict[str, Any]]: ...

    @overload
    async def _process_single_message_content(
        self, type: Literal["documentMessage"], msg_data: dict[str, Any]
    ) -> list[dict[str, Any]]: ...

    async def _process_single_message_content(
        self, type: ACCEPTABLE_TYPES_MESSAGE, msg_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Processa o conteúdo de uma única mensagem (especialmente mídias)"""
        logger.info(f"Tipo da messagem recebida: {type}")
        lst_content: list[dict[str, Any]] = []
        try:
            message_data: Any = msg_data.get(type, "")
            if type == "conversation":
                # Mensagem de texto simples
                lst_content.append(
                    ContentItem(type="input_text", text=message_data).model_dump(
                        exclude_none=True
                    )
                )
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
                        item: ContentItem
                        itemCaption: ContentItem | None = None
                        # Adiciona o item de conteúdo apropriado
                        if type == "imageMessage":
                            # Se houver caption, adiciona como texto também
                            if caption:
                                itemCaption = ContentItem(
                                    type="input_text", text=caption
                                )
                            item = ContentItem(type="input_image", url=public_url)
                        elif type == "audioMessage":
                            # Transforma o audio em texto
                            text_of_audio: str = clientAI.transcribe_audio(public_url)
                            item = ContentItem(type="input_text", text=text_of_audio)
                        elif type == "documentMessage":
                            if caption:
                                itemCaption = ContentItem(
                                    type="input_text", text=caption
                                )

                            item = ContentItem(type="input_file", url=public_url)

                        else:
                            logger.warning("Tipo de mensagem não compativel")
                            raise Exception("Tipo de mensagem não compativel")

                        if itemCaption:
                            lst_content.append(
                                itemCaption.model_dump(exclude_none=True)
                            )
                        lst_content.append(item.model_dump(exclude_none=True))
                    except Exception as e:
                        logger.error(f"Erro ao processar mídia: {e}")
                        raise e
                raise Exception("Não foi enviado o midiaKey ou a url da mídia")
            return lst_content

        except Exception as e:
            logger.error(f"Erro geral no process_input: {e}")
            raise e


# Instância global
message_processor = MessageProcessor()
