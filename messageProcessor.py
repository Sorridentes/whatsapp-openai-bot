import logging
from typing import Any, Literal
from database import redis_queue, mongo_db
from whatsappMessage import WhatsappMessage
from openaiIntegration import clientAI
from evolutionIntegration import clientEvolution
from message import Message
from contentItem import ContentItem
from decrypt import decryptByLink
import base64
import os

logger: logging.Logger = logging.getLogger(__name__)
ACCEPTABLE_TYPES_MESSAGE = Literal[
    "conversation", "audioMessage", "imageMessage", "documentMessage"
]


class MessageProcessor:
    def __init__(self) -> None:
        self.message: Message
        self.zap_message: WhatsappMessage

    async def process_phone_messages(self, phone_number: str):
        """Processa TODAS as mensagens pendentes de um telefone"""
        try:
            raw_messages: list[dict[str, Any]] = redis_queue.get_pending_messages(
                phone_number
            )

            logger.info(
                f"Mensagens recuperadas do Redis para {phone_number}: {len(raw_messages)}"
            )

            if not raw_messages:
                logger.info(f"Nenhuma mensagem pendente para {phone_number}")
                return

            logger.info(
                f"Processando {len(raw_messages)} mensagens em lote para {phone_number}"
            )

            # Processa cada mensagem bruta e converte para ContentItems
            all_content_items: list[ContentItem] = []
            for raw_msg in raw_messages:
                try:
                    processed_content = await self._process_single_message(raw_msg)
                    all_content_items.extend(processed_content)
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem individual: {e}")
                    continue

            if not all_content_items:
                logger.warning(f"Nenhum conteúdo válido processado para {phone_number}")
                return

            # Cria a mensagem com todos os conteúdos (ainda criptografados)
            self.message = Message(role="user", content=all_content_items)

            # Salva no MongoDB APENAS com dados criptografados
            mongo_db.save(
                phone_number=phone_number,
                message_data=self.message.model_dump(exclude_none=True, mode="json"),
            )

            logger.info(f"Mensagem salva no MongoDB para {phone_number}")

            # Processa o lote completo com OpenAI (aqui sim descriptografa)
            await self._process_with_openai(phone_number)

        except Exception as e:
            logger.error(
                f"Erro ao processar mensagens em lote para {phone_number}: {str(e)}",
                exc_info=True,
            )
            raise e

    async def _process_single_message(
        self, raw_message: dict[str, Any]
    ) -> list[ContentItem]:
        """Processa uma única mensagem bruta do Redis e retorna ContentItems (criptografados)"""
        content_items: list[ContentItem] = []

        try:
            # Extrai informações básicas da mensagem
            msg_type = raw_message["data"].get("messageType", "conversation")
            message_data = raw_message["data"].get("message", {})

            logger.info(f"Processando mensagem do tipo: {msg_type}")

            if msg_type == "conversation":
                # Mensagem de texto simples
                text = message_data.get("conversation", "")
                if text.strip():
                    content_items.append(ContentItem(type="input_text", text=text))
                    logger.info(f"Texto processado: {text[:50]}...")

            elif msg_type in ["audioMessage", "imageMessage", "documentMessage"]:
                # Processa mensagens de mídia (mantém dados criptografados)
                media_items = await self._process_encrypted_media(
                    msg_type, message_data
                )
                content_items.extend(media_items)

        except Exception as e:
            logger.error(f"Erro no _process_single_message: {e}")
            raise e

        return content_items

    async def _process_encrypted_media(
        self, type: ACCEPTABLE_TYPES_MESSAGE, message_data: dict[str, Any]
    ) -> list[ContentItem]:
        """Processa mídias mantendo dados criptografados para salvar no MongoDB"""
        content_items: list[ContentItem] = []

        try:
            # Obtém os dados específicos do tipo de mídia
            media_data = message_data.get(type, {})

            encrypted_url = media_data.get("url")
            media_key_b64 = media_data.get("mediaKey")
            mimetype = media_data.get("mimetype")
            caption = media_data.get("caption")

            if not encrypted_url or not media_key_b64:
                logger.warning(f"URL ou mediaKey não encontrados para {type}")
                return content_items

            # Determina o tipo de conteúdo
            if type == "audioMessage":
                content_type = "input_audio"
            elif type == "imageMessage":
                content_type = "input_image"
            else:  # documentMessage
                content_type = "input_file"

            # Se houver caption, adiciona como texto separado
            if caption and caption.strip():
                content_items.append(ContentItem(type="input_text", text=caption))
                logger.info(f"Caption processada: {caption[:50]}...")

            # Adiciona o item de mídia com dados CRIPTOGRAFADOS
            content_items.append(
                ContentItem(
                    type=content_type,
                    url=encrypted_url,  # URL criptografada
                    media_key=media_key_b64,  # Chave para descriptografar depois
                    mimetype=mimetype,
                    # NÃO inclui public_url aqui - será gerada apenas para OpenAI
                )
            )
            logger.info(f"Mídia {content_type} salva com dados criptografados")

        except Exception as e:
            logger.error(f"Erro no _process_encrypted_media: {e}")
            raise e

        return content_items

    async def _process_with_openai(self, phone_number: str):
        """Processa o histórico completo com a OpenAI (descriptografa apenas aqui)"""
        try:
            # Carrega histórico completo do MongoDB
            historical_messages: list[dict[str, Any]] = mongo_db.get_history(
                phone_number, limit=50
            )

            # Prepara TODAS as mensagens para OpenAI (descriptografando mídias)
            all_messages_for_ai: list[dict[str, Any]] = []

            for hist_msg in historical_messages:
                try:
                    # Prepara cada mensagem histórica para OpenAI
                    prepared_msg = await self._prepare_historical_message_for_openai(
                        hist_msg
                    )
                    if prepared_msg:
                        all_messages_for_ai.append(prepared_msg)
                except Exception as e:
                    logger.warning(f"Erro ao preparar mensagem histórica: {e}")
                    continue

            # Cria a mensagem do WhatsApp
            self.zap_message = WhatsappMessage(
                to_number=phone_number, message=self.message
            )

            # Define o histórico completo para a AI (com mídias descriptografadas)
            self.zap_message.history_to_AI = all_messages_for_ai

            logger.info(f"Enviando {len(all_messages_for_ai)} mensagens para OpenAI")

            # Gera resposta da OpenAI
            clientAI.create_response(self.zap_message)

            # Envia resposta via Evolution
            clientEvolution.send_message(self.zap_message)

            # Salva a resposta da assistant no MongoDB (apenas texto)
            mongo_db.save(
                phone_number,
                self.zap_message.message.model_dump(exclude_none=True, mode="json"),
            )

            logger.info(f"Processamento OpenAI concluído para {phone_number}")

        except Exception as e:
            logger.error(f"Erro no _process_with_openai: {str(e)}", exc_info=True)
            raise e

    async def _prepare_historical_message_for_openai(
        self, historical_msg: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepara uma mensagem histórica do MongoDB para a OpenAI"""
        try:
            # Cria uma cópia da mensagem
            prepared_msg: Any = historical_msg.copy()

            # Se a mensagem tem conteúdo, prepara cada item
            if "content" in prepared_msg and isinstance(prepared_msg["content"], list):
                prepared_content: list[dict[str, Any]] = []
                for content_item in prepared_msg["content"]:
                    # Se for mídia do MongoDB, descriptografa temporariamente
                    if content_item.get("type") in [
                        "input_audio",
                        "input_image",
                        "input_file",
                    ]:
                        if content_item.get("url") and content_item.get("media_key"):
                            # Descriptografa para OpenAI
                            openai_item = await self._decrypt_single_media_for_openai(
                                content_item
                            )
                            if openai_item:
                                prepared_content.append(openai_item)
                        else:
                            logger.warning("Item de mídia sem URL ou media_key")
                    else:
                        # Texto usa diretamente
                        prepared_content.append(content_item)

                prepared_msg["content"] = prepared_content

            return prepared_msg

        except Exception as e:
            logger.error(f"Erro ao preparar mensagem histórica: {e}")
            return historical_msg  # Retorna original em caso de erro

    async def _decrypt_single_media_for_openai(
        self, media_item: dict[str, Any]
    ) -> dict[str, Any]:
        """Descriptografa um único item de mídia para OpenAI"""
        try:
            media_type_map: dict[str, Any] = {
                "input_audio": "audio",
                "input_image": media_item.get("mimetype") or "image",
                "input_file": "document",
            }

            media_type = media_type_map.get(media_item["type"])
            if not media_type:
                logger.warning(f"Tipo de mídia não mapeado: {media_item['type']}")
                return media_item

            public_url = decryptByLink(
                link=media_item["url"],
                mediaKey=base64.b64decode(media_item["media_key"]),
                mediaType=media_type,
            )

            # Agenda limpeza
            self._schedule_file_cleanup(public_url)

            # Retorna item com URL pública temporária
            if media_item["type"] == "input_audio":
                file_path = f"./static/{public_url.split('/')[-1]}"
                text_of_audio = clientAI.transcribe_audio(file_path)
                openai_item = {"type": "input_text", "text": text_of_audio}
            else:
                print(media_item["type"])
                openai_item: dict[str, Any] = {
                    "type": media_item["type"],
                    "url": public_url,
                    "mimetype": media_item.get("mimetype"),
                }
            return openai_item

        except Exception as e:
            logger.error(f"Erro ao descriptografar mídia para OpenAI: {e}")
            return media_item  # Retorna original em caso de erro

    def _schedule_file_cleanup(self, file_path_network: str):
        """Agenda limpeza do arquivo temporário após processamento"""
        import threading
        import time

        def cleanup():
            # Aguarda um tempo razoável para o processamento da OpenAI
            time.sleep(10)  # 10 segundos deve ser suficiente
            file_path = "./static/" + file_path_network.split("/")[-1]
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Arquivo temporário removido: {file_path}")
                else:
                    logger.warning(f"Arquivo temporário não encontrado: {file_path}")
            except Exception as e:
                logger.error(f"Erro ao remover arquivo temporário {file_path}: {e}")

        # Executa a limpeza em thread separada
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()


# Instância global
message_processor = MessageProcessor()
