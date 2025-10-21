from pymongo import MongoClient
from redis import Redis
from config import Config
import logging
import json
from typing import Any, Literal
from datetime import datetime, timedelta, timezone

logger: logging.Logger = logging.getLogger(__name__)


class MongoDB:
    def __init__(self) -> None:
        self.client: MongoClient[Any] = MongoClient(Config.MONGODB_URI)
        self.db = self.client[Config.MONGO_INITDB_DATABASE]
        self.conversations = self.db["conversations"]
        self.temp_conversation = self.db["media_cache"]

        # Índices para otimizar as consultas de expiração
        self._create_indexes()

    def _create_indexes(self) -> None:
        """Cria índice para melhor performance nas consultas de expiração"""
        try:
            # Índice para expiração de conversas
            self.conversations.create_index([("phone_number", 1), ("expires_at", 1)])

            # Índice para expiração de mídias
            self.temp_conversation.create_index([("expires_at", 1)])

            # Índice para busca por telefone
            self.conversations.create_index([("phone_number", 1)])

            logger.info("Índice do MongoDB criados/verificados com sucesso")

        except Exception as e:
            logger.error(f"Erro ao criar índices: {str(e)}")

    def save(
        self,
        phone_number: str,
        message_data: dict[str, Any],
        db_type: Literal["conversation", "temp_conversation"] = "conversation",
    ) -> None:
        """Salva uma mensagem no histórico da conversa com expiração de 1 dia"""
        db = self.conversations if db_type == "conversation" else self.temp_conversation
        try:
            # Data de expiração: 1 dia a partir de agora
            expires_at = datetime.now(timezone.utc) + timedelta(days=1)

            db.update_one(
                {"phone_number": phone_number},
                {
                    "$push": {
                        "messages": {
                            "$each": [message_data],
                            "$slice": -100,  # Mantém as últimas 100 mensagens
                        }
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now(timezone.utc),
                    },
                    "$set": {
                        "update_at": datetime.now(timezone.utc),
                        "expires_at": expires_at,  # SEMPRE atuliza a expiração
                    },
                },
                upsert=True,
            )
            logger.info(f"Conversa salva para {phone_number} - Expira em {expires_at}")
        except Exception as e:
            logger.error(f"Erro ao salvar conversa: %s", e)
            raise e

    def get_history(
        self,
        phone_number: str,
        db_type: Literal["conversation", "temp_conversation"] = "conversation",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Recupera o histórico de conversa, filtrando mensagens expiradas"""
        db = self.conversations if db_type == "conversation" else self.temp_conversation
        try:
            # Busca a conversa do telefone
            result = db.find_one(
                {"phone_number": phone_number},
                {"messages": {"$slice": -limit}},  # Pega as últimas 'limit' mensagens
            )

            if not result:
                return []

            # Filtra apenas mensagens não expiradas
            current_time = datetime.now(timezone.utc)
            valid_messages = [
                msg
                for msg in result.get("messages", [])
                if msg.get("message_expires_at", current_time + timedelta(days=1))
                > current_time
                or db_type == "temp_conversation"
            ]

            logger.info(
                f"Recuperadas {len(valid_messages)} mensagens válidas para {phone_number}"
            )
            return valid_messages

        except Exception as e:
            logger.error(f"Erro ao recuperar histórico: {str(e)}")
            raise e


class RedisQueue:
    def __init__(self):
        self.redis: Redis = Redis.from_url(Config.REDIS_URL)  # type: ignore[arg-type]

    def add_message(self, id: str, message_data: dict[str, Any]) -> None:
        """Adiciona mensagem à fila do Redis"""
        try:
            key = f"whatsapp:{id}"
            message_json = json.dumps(message_data, ensure_ascii=False)
            self.redis.rpush(key, message_json)

            # Define expiração para a fila de mensagens (batch processing)
            self.redis.expire(key, 60)

            logger.info(f"Mensagem adicionada à fila para {id}, chave: {key}")  # DEBUG
            logger.debug(f"Conteúdo da mensagem: {message_data}")  # DEBUG
        except Exception as e:
            logger.error(
                f"Erro ao adicionar mensagem ao Redis: {str(e)}", exc_info=True
            )
            raise e

    def get_pending_messages(self, phone_number: str) -> list[dict[str, Any]]:
        """Recupera todas as mensagens pendentes e limpa a fila"""
        try:
            key: str = f"whatsapp:{phone_number}"
            logger.info(f"Buscando mensagens com chave: {key}")  # DEBUG

            # Verifica se a chave existe
            if not self.redis.exists(key):
                logger.info(f"Chave {key} não encontrada no Redis")
                return []

            redis_messages: list[bytes] = self.redis.lrange(key, 0, -1)  # type: ignore
            logger.info(
                f"Encontradas {len(redis_messages)} mensagens no Redis"
            )  # DEBUG

            self.redis.delete(key)

            result: list[dict[str, Any]] = []
            for msg_bytes in redis_messages:
                try:
                    msg_str = msg_bytes.decode("utf-8")
                    message_dict: dict[str, Any] = json.loads(msg_str)
                    result.append(message_dict)
                    logger.debug(f"Mensagem decodificada: {message_dict}")  # DEBUG
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"Erro ao decodificar mensagem do Redis: {e}")
                    continue
            return result
        except Exception as e:
            logger.error(f"Erro ao recuperar mensagens do Redis: {str(e)}")
            raise e


# Instâncias globais
mongo_db = MongoDB()
redis_queue = RedisQueue()
