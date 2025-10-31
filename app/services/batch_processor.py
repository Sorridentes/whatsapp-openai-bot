# batch_processor.py
import asyncio
import logging
import time
from typing import Dict, Any

from app.core.config import Config
from .messageProcessor import MessageProcessor
from app.database import redis_queue

logger = logging.getLogger(__name__)


class GlobalBatchProcessor:
    def __init__(self):
        self.processing_tasks: Dict[str, asyncio.Task[Any]] = {}
        self.batch_timeout = Config.BATCH_PROCESSING_DELAY
        self.message_processor = MessageProcessor()
        self._shutting_down = False
        self._batch_monitor_task: asyncio.Task[Any] | None = None

    async def start_monitoring(self):
        """Inicia o monitoramento contínuo dos batches"""
        self._batch_monitor_task = asyncio.create_task(self._monitor_batches())

    async def add_message(self, phone_number: str, message_data: dict[str, Any]):
        """Adiciona mensagem ao Redis e agenda processamento"""
        if self._shutting_down:
            return

        try:
            # Adiciona a mensagem ao Redis (método existente)
            redis_queue.add_message(phone_number, message_data)

            # Agenda o processamento deste telefone
            await self._schedule_batch_processing(phone_number)

            logger.info(f"Mensagem adicionada e agendada para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem para {phone_number}: {e}")
            raise

    async def _schedule_batch_processing(self, phone_number: str):
        """Agenda o processamento do batch para este telefone"""
        try:
            # Define um timestamp de expiração no Redis
            processing_key = f"batch_processing:{phone_number}"
            expiry_time = time.time() + self.batch_timeout

            logger.info(f"AGENDANDO: {phone_number} -> expira em {self.batch_timeout}")

            # Usa SET com NX para evitar agendamentos duplicados
            scheduled = await asyncio.get_event_loop().run_in_executor(
                None, lambda: redis_queue.redis.set(processing_key, str(expiry_time))
            )

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: redis_queue.redis.expireat(
                    processing_key, int(time.time() + 60)
                ),
            )

            if scheduled:
                logger.info(
                    f"Batch agendado para {phone_number} em {self.batch_timeout}s"
                )
            else:
                logger.info(f"Expiração do batch atualizado para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao agendar batch para {phone_number}: {e}")

    async def _monitor_batches(self):
        """Monitora continuamente os batches prontos para processamento"""
        if not self._shutting_down:
            logger.info(f"--- Monitoramento de batch iniciado")

        while not self._shutting_down:
            try:
                # Encontra batches que expiraram (devem ser processados)
                current_time = time.time()
                batch_keys: list[
                    bytes
                ] = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: redis_queue.redis.keys("batch_processing:*"),  # type: ignore
                )

                if batch_keys:
                    logger.debug(
                        f"Monitor: encontradas {len(batch_keys)} chaves de batch"
                    )

                for key in batch_keys:
                    try:
                        # Verifica se o batch expirou
                        expiry_str: (
                            Any
                        ) = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: redis_queue.redis.get(key)
                        )

                        if expiry_str and float(expiry_str) <= current_time:
                            # Remove a chave e processa o batch
                            phone_number = key.decode().split(":")[1]

                            removed = await asyncio.get_event_loop().run_in_executor(
                                None, lambda: redis_queue.redis.delete(key)
                            )

                            if removed:
                                await self._process_scheduled_batch(phone_number)

                    except Exception as e:
                        logger.error(f"Erro ao processar batch key {key}: {e}")
                        continue

                # Espera um curto período antes da próxima verificação
                await asyncio.sleep(1)  # 1s

            except Exception as e:
                logger.error(f"Erro no monitor de batches: {e}")
                await asyncio.sleep(1)

    async def _process_scheduled_batch(self, phone_number: str):
        """Processa um batch agendado"""
        try:
            # Verifica se há mensagens pendentes
            pending_count: int | Any = await asyncio.get_event_loop().run_in_executor(
                None, lambda: redis_queue.redis.llen(f"whatsapp:{phone_number}")
            )

            if pending_count > 0:
                logger.info(
                    f"Processando batch agendado para {phone_number} com {pending_count} mensagens"
                )

                # Usa o MessageProcessor existente para processar
                await self.message_processor.process_phone_messages(phone_number)

                logger.info(f"Batch processado com sucesso para {phone_number}")
            else:
                logger.info(f"Nenhuma mensagem pendente para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao processar batch agendado para {phone_number}: {e}")

    async def stop_monitoring(self):
        """Para o monitoramento gracefuly"""
        self._shutting_down = True
        if self._batch_monitor_task and not self._batch_monitor_task.done():
            self._batch_monitor_task.cancel()
            try:
                await self._batch_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitor de batches parado")
