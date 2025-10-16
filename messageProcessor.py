import logging
import asyncio
from typing import Any
from database import redis_queue, mongo_db
from whatsappMessage import WhatsappMessage
from message import Message
from openaiIntegration import OpenaiIntegration
from evolutionIntegration import EvolutionIntegration
from decrypt import decryptByLink
from config import Config

logger: logging.Logger = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(self):
        self.openai_integration = OpenaiIntegration()
        self.evolution_integration = EvolutionIntegration()

    async def process_phone_messages(self, phone_number: str):
        """Processa TODAS as mensagens pendentes de um telefone de uma vez"""
        try:
            # Aguarda o timeout para agrupar mensagens
            await asyncio.sleep(Config.BATCH_PROCESSING_DELAY)

            # Recupera todas as mensagens pendentes
            pending_messages = redis_queue.get_pending_messages(phone_number)

            if not pending_messages:
                logger.info(f"Nenhuma mensagem pendente para {phone_number}")
                return

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
            self.openai_integration.create_response(zap_message)

            # Envia UMA resposta via Evolution
            self.evolution_integration.send_message(zap_message)

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
        self, msg_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Processa o conteúdo de uma única mensagem (especialmente mídias)"""
        try:
            message_dict = msg_data["message"].copy()

            # Processa mídias se existirem
            for content_item in message_dict.get("content", []):
                if content_item.get("type") in [
                    "input_image",
                    "input_file",
                ] and content_item.get("media_key"):
                    media_type = (
                        "image/jpeg"
                        if content_item["type"] == "input_image"
                        else "document"
                    )

                    # Descriptografa e obtém URL temporária
                    public_url = decryptByLink(
                        link=content_item.get("image_url")
                        or content_item.get("file_url"),
                        mediaKey=content_item["media_key"],
                        mediaType=media_type,
                    )

                    # Salva referência no MongoDB
                    media_id = mongo_db.save_media_reference(
                        {
                            "phone_number": "temp",  # Será atualizado depois
                            "original_url": content_item.get("image_url")
                            or content_item.get("file_url"),
                            "public_url": public_url,
                            "media_key": content_item["media_key"],
                            "media_type": media_type,
                            "processed": False,
                        }
                    )

                    # Atualiza a URL para a pública temporária
                    if content_item["type"] == "input_image":
                        content_item["image_url"] = public_url
                    else:
                        content_item["file_url"] = public_url

                    content_item["media_id"] = media_id

            return message_dict

        except Exception as e:
            logger.error(f"Erro ao processar conteúdo da mensagem: {str(e)}")
            return msg_data["message"]  # Retorna original em caso de erro


# Instância global
message_processor = MessageProcessor()
