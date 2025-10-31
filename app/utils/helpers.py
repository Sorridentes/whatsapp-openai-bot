from typing import Any
import logging
from app import batch_processor, async_executor


# Configuração do log
logger: logging.Logger = logging.getLogger(__name__)

# Variável global para controlar o monitoramento
_monitor_started = False


async def start_batch_monitor():
    """Inicializa o monitor de batches no mesmo event loop"""
    global _monitor_started
    if not _monitor_started:
        logger.info("INICIANDO MONITOR DE BATCHES...")
        try:
            await batch_processor.start_monitoring()
            _monitor_started = True
            logger.info("MONITOR INICIADO COM SUCESSO")
        except Exception as e:
            logger.error(f"FALHA AO INICIAR MONITOR: {e}")


def async_processor(phone_number: str, payload: dict[str, Any]):
    """Envia mensagem para processamento assíncrono"""
    try:
        # Submete a tarefa ao executor customizado
        async_executor.submit(_process_message_async, phone_number, payload)
        logger.info(f"Mensagem enviada para processamento: {phone_number}")

    except Exception as e:
        logger.error(f"Erro ao submeter mensagem para processamento: {e}")


# Função assíncrona que será executada
async def _process_message_async(phone_number: str, payload: dict[str, Any]):
    """Processa uma mensagem de forma assíncrona"""
    try:
        await batch_processor.add_message(phone_number, payload)
        logger.info(f"Mensagem processada com sucesso: {phone_number}")
    except Exception as e:
        logger.error(f"Erro no processamento assíncrono para {phone_number}: {e}")
        raise
