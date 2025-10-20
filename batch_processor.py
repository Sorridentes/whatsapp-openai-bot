# batch_processor.py
import asyncio
import logging
from typing import Dict, Any
from database import redis_queue
from messageProcessor import MessageProcessor
from config import Config

logger = logging.getLogger(__name__)


class GlobalBatchProcessor:
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue[Any]] = {}
        self.processing_tasks: Dict[str, asyncio.Task[Any]] = {}
        self.batch_timeout = Config.BATCH_PROCESSING_DELAY
        self.message_processor = MessageProcessor()
        self._shutting_down = False

    async def add_message(self, phone_number: str, message_data: dict[str, Any]):
        """Adiciona mensagem à fila do telefone"""
        if self._shutting_down:
            return

        if phone_number not in self.queues:
            self.queues[phone_number] = asyncio.Queue()
            # Inicia task de processamento para este telefone
            self.processing_tasks[phone_number] = asyncio.create_task(
                self._process_batch_for_phone(phone_number),
                name=f"batch_processor_{phone_number}",
            )
            logger.info(f"Iniciado batch processor para {phone_number}")

        await self.queues[phone_number].put(message_data)
        logger.info(f"Mensagem adicionada à fila de {phone_number}")

    async def _process_batch_for_phone(self, phone_number: str):
        queue = self.queues[phone_number]

        try:
            while not self._shutting_down:
                batch: list[dict[str, Any]] = []

                try:
                    # Coleta a PRIMEIRA mensagem
                    first_message = await queue.get()
                    batch.append(first_message)

                    # Loop que reseta o timer a cada nova mensagem
                    while True:
                        try:
                            # Espera por novas mensagens por até batch_timeout segundos
                            # Se chegar mensagem, reseta o timer. Se timeout, processa.
                            additional_msg = await asyncio.wait_for(
                                queue.get(), timeout=self.batch_timeout
                            )
                            batch.append(additional_msg)
                            logger.info(
                                f"Mensagem adicional adicionada ao lote para {phone_number} - timer resetado"
                            )
                            # TIMER RESETADO - volta a esperar batch_timeout segundos

                        except asyncio.TimeoutError:
                            # Não chegou nova mensagem por batch_timeout segundos - PROCESSAR
                            break

                    # Processa o lote completo após período de inatividade
                    if batch:
                        logger.info(
                            f"Processando lote de {len(batch)} mensagens para {phone_number} (5s sem novas mensagens)"
                        )
                        await self._process_batch(phone_number, batch)

                except asyncio.CancelledError:
                    logger.info(f"Batch processor para {phone_number} cancelado")
                    if batch:
                        await self._process_batch(phone_number, batch)
                    break
                except Exception as e:
                    logger.error(f"Erro no batch processor para {phone_number}: {e}")
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Erro crítico no batch processor para {phone_number}: {e}")
        finally:
            await self._cleanup_phone(phone_number)

    async def _process_batch(self, phone_number: str, batch: list[dict[str, Any]]):
        """Processa um lote de mensagens usando o MessageProcessor existente"""
        try:
            logger.info(
                f"Processando lote de {len(batch)} mensagens para {phone_number}"
            )

            # Salva todas as mensagens no Redis primeiro
            for message_data in batch:
                redis_queue.add_message(phone_number, message_data)

            # Chama o método original do MessageProcessor
            await self.message_processor.process_phone_messages(phone_number)

            logger.info(f"Lote processado com sucesso para {phone_number}")

        except Exception as e:
            logger.error(f"Erro ao processar lote para {phone_number}: {e}")

    async def _cleanup_phone(self, phone_number: str):
        """Limpa recursos para um telefone"""
        try:
            if phone_number in self.queues:
                # Processa mensagens restantes na queue
                queue = self.queues[phone_number]
                remaining_messages: list[dict[str, Any]] = []
                while not queue.empty():
                    try:
                        msg = queue.get_nowait()
                        remaining_messages.append(msg)
                    except asyncio.QueueEmpty:
                        break

                if remaining_messages:
                    await self._process_batch(phone_number, remaining_messages)

                del self.queues[phone_number]

            if phone_number in self.processing_tasks:
                task = self.processing_tasks[phone_number]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.processing_tasks[phone_number]

        except Exception as e:
            logger.error(f"Erro no cleanup para {phone_number}: {e}")

    async def shutdown(self):
        """Desliga o batch processor gracefuly"""
        self._shutting_down = True
        logger.info("Iniciando shutdown do GlobalBatchProcessor...")

        # Para todas as tasks
        for phone_number in list(self.processing_tasks.keys()):
            await self._cleanup_phone(phone_number)

        logger.info("GlobalBatchProcessor shutdown completo")


# Instância global
batch_processor = GlobalBatchProcessor()
