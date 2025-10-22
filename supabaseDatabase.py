from config import Config
from supabase import create_client
import supabase
import logging
from typing import Any
from datetime import datetime, timedelta, timezone

logger: logging.Logger = logging.getLogger(__name__)


class SupabaseDatabase:
    def __init__(self) -> None:
        self.client: supabase.Client | None = None
        self.conversations_table = "conversations"
        self.is_healthy = False
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Inicializa a conexão com o Supabase"""
        try:
            if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
                logger.error("URL ou chave do Supabase não configurados")
                self.is_healthy = False
                return

            self.client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

            # Testa a conexão
            self.client.table(self.conversations_table).select("count", count="exact").limit(1).execute()  # type: ignore
            self.is_healthy = True
            logger.info("Conexão com Supabase estabelecida com sucesso")

        except Exception as e:
            self.is_healthy = False
            logger.error(f"Falha na conexão com Supabase: {str(e)}")

    def check_health(self) -> bool:
        """Verifica se o Supabase está respondendo"""
        return self.is_healthy

    def save(
        self,
        phone_number: str,
        message_data: dict[str, Any],
    ) -> None:
        """Salva uma mensagem no Supabase com expiração de 1 dia"""
        if not self.is_healthy or not self.client:
            raise ConnectionError("Supabase não está disponível")

        table = self.conversations_table

        try:
            # Data de expiração: 1 dia a partir de agora
            expires_at = datetime.now(timezone.utc) + timedelta(days=1)

            # Busca conversa existente
            existing: Any = (
                self.client.table(table)
                .select("*")
                .eq("phone_number", phone_number)
                .execute()
            )

            if existing.data:
                # Atualiza conversa existente
                conversation = existing.data[0]
                messages = conversation.get("messages", [])
                messages.append(message_data)
                # Mantém apenas as últimas 100 mensagens
                messages = messages[-100:]

                self.client.table(table).update(
                    {
                        "messages": messages,
                        "update_at": datetime.now(timezone.utc).isoformat(),
                        "expires_at": expires_at.isoformat(),
                    }
                ).eq("phone_number", phone_number).execute()
            else:
                # Cria nova conversa
                self.client.table(table).insert(
                    {
                        "phone_number": phone_number,
                        "messages": [message_data],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "update_at": datetime.now(timezone.utc).isoformat(),
                        "expires_at": expires_at.isoformat(),
                    }
                ).execute()

            logger.info(f"Conversa salva no Supabase para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao salvar conversa no Supabase: {e}")
            raise e

    def get_history(
        self,
        phone_number: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Recupera o histórico de conversa do Supabase"""
        if not self.is_healthy or not self.client:
            raise ConnectionError("Supabase não está disponível")

        table = self.conversations_table

        try:
            result: Any = (
                self.client.table(table)
                .select("*")
                .eq("phone_number", phone_number)
                .execute()
            )

            if not result.data:
                return []

            conversation = result.data[0]
            all_messages = conversation.get("messages", [])

            # Filtra mensagens expiradas
            current_time = datetime.now(timezone.utc)
            valid_messages: list[Any] = []

            for msg in all_messages:
                msg_expires = msg.get("message_expires_at")
                if msg_expires:
                    try:
                        expires_date = datetime.fromisoformat(
                            msg_expires.replace("Z", "+00:00")
                        )
                        if expires_date > current_time:
                            valid_messages.append(msg)
                    except (ValueError, AttributeError):
                        # Se não conseguir parsear a data, inclui a mensagem
                        valid_messages.append(msg)
                else:
                    # Mensagens sem data de expiração são incluídas
                    valid_messages.append(msg)

            # Aplica limite
            valid_messages = valid_messages[-limit:]

            logger.info(
                f"Recuperadas {len(valid_messages)} mensagens do Supabase para {phone_number}"
            )
            return valid_messages

        except Exception as e:
            logger.error(f"Erro ao recuperar histórico do Supabase: {e}")
            raise e
