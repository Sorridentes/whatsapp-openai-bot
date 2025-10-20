from concurrent.futures import ThreadPoolExecutor
import asyncio
import threading
from typing import Dict, Any, Callable
import logging

logger: logging.Logger = logging.getLogger(__name__)


# ThreadPoolExecutor customizado
class AsyncThreadPoolExecutor:
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.thread_loops: Dict[str, asyncio.AbstractEventLoop] = {}
        self.lock = threading.Lock()

    def get_loop_for_thread(self) -> asyncio.AbstractEventLoop:
        """Obtém ou cria um loop para a thread atual"""
        thread_name = threading.current_thread().name

        with self.lock:
            if thread_name not in self.thread_loops:
                # Cria novo loop para esta thread
                loop = asyncio.new_event_loop()
                self.thread_loops[thread_name] = loop
                logger.info(f"Novo loop criado para thread: {thread_name}")
            else:
                loop = self.thread_loops[thread_name]

            # Verifica se o loop está fechado
            if loop.is_closed():
                logger.warning(
                    f"Loop fechado detectado para {thread_name}, recriando..."
                )
                loop = asyncio.new_event_loop()
                self.thread_loops[thread_name] = loop

            return loop

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        """Submete uma tarefa para execução assíncrona"""

        def run_with_loop():
            loop = self.get_loop_for_thread()
            asyncio.set_event_loop(loop)

            try:
                # Verifica se é uma coroutine
                if asyncio.iscoroutinefunction(fn):
                    return loop.run_until_complete(fn(*args, **kwargs))
                else:
                    return fn(*args, **kwargs)
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    logger.warning("Event loop fechado, recriando...")
                    # Recria o loop e tenta novamente
                    with self.lock:
                        new_loop = asyncio.new_event_loop()
                        self.thread_loops[threading.current_thread().name] = new_loop
                        asyncio.set_event_loop(new_loop)
                    return new_loop.run_until_complete(fn(*args, **kwargs))
                raise
            except Exception as e:
                logger.error(f"Erro na execução da task: {e}")
                raise

        return self.executor.submit(run_with_loop)

    def shutdown(self, wait: bool = True):
        """Desliga o executor gracefuly"""
        logger.info("Desligando AsyncThreadPoolExecutor...")

        with self.lock:
            for thread_name, loop in self.thread_loops.items():
                try:
                    if not loop.is_closed():
                        # Tenta finalizar tasks pendentes
                        pending = asyncio.all_tasks(loop)
                        if pending:
                            logger.info(
                                f"Cancelando {len(pending)} tasks pendentes em {thread_name}"
                            )
                            for task in pending:
                                task.cancel()

                        # Fecha o loop
                        loop.close()
                        logger.info(f"Loop fechado para thread: {thread_name}")
                except Exception as e:
                    logger.error(f"Erro ao fechar loop para {thread_name}: {e}")

            self.thread_loops.clear()

        self.executor.shutdown(wait=wait)


# Instância global do executor customizado
async_executor = AsyncThreadPoolExecutor(max_workers=10)
