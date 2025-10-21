import logging
from typing import Any

from mongoDB import MongoDB
from supabaseDatabase import SupabaseDatabase
from redisQueue import RedisQueue

logger: logging.Logger = logging.getLogger(__name__)


class Database:
    def __init__(self) -> None:
        self.mongo_db = MongoDB()
        self.supabase_db = SupabaseDatabase()
        self.current_db = self._select_database()
        self.redis = RedisQueue()

    def _select_database(self):
        """Seleciona o banco de dados baseado na disponibilidade"""
        # Verifica MongoDB primeiro
        if self.mongo_db.check_health():
            logger.info("Usando MongoDB como banco de dados principal")
            return self.mongo_db

        # Se MongoDB falhar, tenta Supabase
        if self.supabase_db.check_health():
            logger.info("MongoDB indisponível, usando Supabase como fallback")
            return self.supabase_db

        # Se ambos falharem, levanta erro
        raise ConnectionError(
            "Nenhum banco de dados disponível (MongoDB e Supabase offline)"
        )

    def get_current_database(self) -> str:
        """Retorna qual banco está sendo usado atualmente"""
        return "MongoDB" if self.current_db == self.mongo_db else "Supabase"

    def check_both_health(self) -> dict[str, Any]:
        """Verifica a saúde de ambos os bancos"""
        return {
            "mongodb": self.mongo_db.check_health(),
            "supabase": self.supabase_db.check_health(),
            "current": self.get_current_database(),
            "redis": self.redis.check_health(),
        }


# Instâncias globais
mongo_db = Database().current_db
redis_queue = Database().redis
