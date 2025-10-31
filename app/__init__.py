from flask import Flask
import logging
import sys

from app.services.threadPoolExecutor import AsyncThreadPoolExecutor
from app.services.batch_processor import GlobalBatchProcessor

logger: logging.Logger = logging.getLogger(__name__)


def configure_logging():
    """Configura o sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt=r"%d-%m-%Y %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app_debug.log"),
        ],
    )


def create_app():
    """Cria a aplicação Flask"""
    logger.info("Iniciando configuração de rotas")
    app = Flask(__name__)

    # Configura logging
    configure_logging()

    # Configuração das rotas
    from .api.routes import main_bp
    from .api.webhook import webhook_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(webhook_bp, url_prefix="/v1/webhook")

    return app


# Instância global
batch_processor = GlobalBatchProcessor()
async_executor = AsyncThreadPoolExecutor(max_workers=10)
