from pymongo import MongoClient
from app.core.config import Config
import logging
from typing import Any
from datetime import datetime, timedelta, timezone

logger: logging.Logger = logging.getLogger(__name__)


class MongoDB:
    def __init__(self) -> None:
        self.client: MongoClient[Any] | None = None
        self.db = None
        self.conversations = None
        self.is_healthy = False
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Inicializa a conexão com o MongoDB e verifica saúde"""
        from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

        try:
            self.client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
            # Testa a conexão imediatamente
            self.client.admin.command("ping")
            self.db = self.client[Config.MONGO_INITDB_DATABASE]
            self.conversations = self.db["conversations"]
            self.is_healthy = True

            # Cria índices apenas se a conexão estiver saudável
            self._create_indexes()
            logger.info("Conexão com MongoDB estabelecida com sucesso")

        except (ServerSelectionTimeoutError, ConnectionFailure, Exception) as e:
            self.is_healthy = False
            logger.error(f"Falha na conexão com MongoDB: {str(e)}")
            # Mantém as referências para evitar erros, mas marca como não saudável
            if self.client:
                self.db = self.client[Config.MONGO_INITDB_DATABASE]
                self.conversations = self.db["conversations"]

    def check_health(self) -> bool:
        """Verifica se o MongoDB está respondendo"""
        return self.is_healthy

    def _create_indexes(self) -> None:
        """Cria índice para melhor performance nas consultas de expiração"""
        if not self.is_healthy or self.conversations is None:
            raise ConnectionError("MongoDB não está disponível")

        try:
            # Índice para expiração de conversas
            self.conversations.create_index([("phone_number", 1), ("expires_at", 1)])

            # Índice para busca por telefone
            self.conversations.create_index([("phone_number", 1)])

            logger.info("Índice do MongoDB criados/verificados com sucesso")

        except Exception as e:
            logger.error(f"Erro ao criar índices: {str(e)}")

    def save(
        self,
        phone_number: str,
        message_data: dict[str, Any],
    ) -> None:
        """Salva uma mensagem no histórico da conversa com expiração de 1 dia"""
        if not self.is_healthy or self.conversations is None:
            raise ConnectionError("MongoDB não está disponível")

        db = self.conversations
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
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Recupera o histórico de conversa, filtrando mensagens expiradas"""
        if not self.is_healthy or self.conversations is None:
            raise ConnectionError("MongoDB não está disponível")

        db = self.conversations
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
            ]

            logger.info(
                f"Recuperadas {len(valid_messages)} mensagens válidas para {phone_number}"
            )
            return valid_messages

        except Exception as e:
            logger.error(f"Erro ao recuperar histórico: {str(e)}")
            raise e
