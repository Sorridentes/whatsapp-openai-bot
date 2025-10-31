import logging

from app.database.mongoDB import MongoDB
from app.database.redisQueue import RedisQueue
from app.database.supabaseApp import Supabase


logger: logging.Logger = logging.getLogger(__name__)


def _select_database():
    """Seleciona o banco de dados baseado na disponibilidade"""
    # Inicia os bancos
    mongo_db = MongoDB()
    # Verifica MongoDB primeiro
    if mongo_db.check_health():
        logger.info("Usando MongoDB como banco de dados principal")
        return mongo_db

    supabase_db = Supabase()

    # Se MongoDB falhar, tenta Supabase
    if supabase_db.check_health():
        logger.info("MongoDB indisponível, usando Supabase como fallback")
        return supabase_db

    raise ConnectionError(
        "Nenhum banco de dados disponível (MongoDB E Supabase offiline)"
    )


db_current = _select_database()
redis_queue = RedisQueue()
