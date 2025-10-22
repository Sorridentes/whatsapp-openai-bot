from redis import Redis
from config import Config
import logging
import json
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)


class RedisQueue:
    def __init__(self):
        self.redis: Redis = Redis.from_url(  # type: ignore[arg-type]
            Config.REDIS_URL,
            socket_connect_timeout=5,  # 5 segundos timeout
            socket_timeout=5,
            retry_on_timeout=True,
            max_connections=10,
        )
        self.is_healthy = False
        self.check_health()

    def check_health(self) -> bool:
        """Verifica se o Redis está respondendo"""
        try:
            # Testa a conexão
            self.redis.ping()  # type: ignore
            self.is_healthy = True
            logger.info("Conexão com Redis estabelecida com sucesso")
        except (ConnectionError, TimeoutError, Exception) as e:
            self.is_healthy = False
            logger.error(f"Falha na conexão com Redis: {str(e)}")
        finally:
            return self.is_healthy

    def add_message(self, id: str, message_data: dict[str, Any]) -> None:
        """Adiciona mensagem à fila do Redis com verificação de saúde"""
        if not self.is_healthy:
            raise ConnectionError("Redis não está disponível")

        try:
            key = f"whatsapp:{id}"
            message_json = json.dumps(message_data, ensure_ascii=False)
            self.redis.rpush(key, message_json)

            # Define expiração para a fila de mensagens (batch processing)
            self.redis.expire(key, 60)

            logger.info(f"Mensagem adicionada à fila para {id}, chave: {key}")
            logger.debug(f"Conteúdo da mensagem: {message_data}")
        except (ConnectionError, TimeoutError) as e:
            self.is_healthy = False
            logger.error(f"Erro de conexão ao adicionar mensagem ao Redis: {str(e)}")
            raise e
        except Exception as e:
            logger.error(
                f"Erro ao adicionar mensagem ao Redis: {str(e)}", exc_info=True
            )
            raise e

    def get_pending_messages(self, phone_number: str) -> list[dict[str, Any]]:
        """Recupera todas as mensagens pendentes e limpa a fila com verificação de saúde"""
        if not self.is_healthy:
            raise ConnectionError("Redis não está disponível")

        try:
            key: str = f"whatsapp:{phone_number}"
            logger.info(f"Buscando mensagens com chave: {key}")

            # Verifica se a chave existe
            if not self.redis.exists(key):
                logger.info(f"Chave {key} não encontrada no Redis")
                return []

            redis_messages: list[bytes] = self.redis.lrange(key, 0, -1)  # type: ignore
            logger.info(f"Encontradas {len(redis_messages)} mensagens no Redis")

            self.redis.delete(key)

            result: list[dict[str, Any]] = []
            for msg_bytes in redis_messages:
                try:
                    msg_str = msg_bytes.decode("utf-8")
                    message_dict: dict[str, Any] = json.loads(msg_str)
                    result.append(message_dict)
                    logger.debug(f"Mensagem decodificada: {message_dict}")
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"Erro ao decodificar mensagem do Redis: {e}")
                    continue
            return result

        except (ConnectionError, TimeoutError) as e:
            self.is_healthy = False
            logger.error(f"Erro de conexão ao recuperar mensagens do Redis: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Erro ao recuperar mensagens do Redis: {str(e)}")
            raise e
