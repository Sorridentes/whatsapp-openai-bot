from typing import Any
import logging
import asyncio
import threading
import signal
from app.utils.helpers import start_batch_monitor
from waitress import serve
from app import batch_processor, create_app


logger: logging.Logger = logging.getLogger(__name__)

# Variável global para controlar o monitor
_shutdown_event = asyncio.Event()


async def main():
    """Função principal assíncrona"""
    try:
        # Inicia o monitor
        await start_batch_monitor()

        # Cria a aplicação Flask
        app = create_app()
        logger.info("Iniciando servidor Flask na porta 8080...")

        # Executa o Waitress em thread separada para não bloquear
        def run_server():
            serve(app, host="0.0.0.0", port=8080)

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Aguarda até que seja sinalizado para desligar
        await _shutdown_event.wait()

    except asyncio.CancelledError:
        logger.info("Recebido sinal de cancelamento")
    finally:
        await batch_processor.stop_monitoring()
        logger.info("Aplicação finalizada gracefuly")


def signal_handler(signum: Any, frame: Any):
    """Handler para sinais de desligamento"""
    logger.info(f"Recebido sinal {signum}, desligando...")
    _shutdown_event.set()


if __name__ == "__main__":
    # Registra handlers para sinais de desligamento
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servidor interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro não esperado: {e}", exc_info=True)
    finally:
        logger.info("Aplicação finalizada")
