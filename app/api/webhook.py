from flask import Blueprint, request, jsonify
import logging
from typing import Any, Dict

from app.utils import validators
from app.utils.helpers import async_processor

logger: logging.Logger = logging.getLogger(__name__)

# Cria um Blueprint para webhooks
webhook_bp = Blueprint("webhook", __name__)


# Rota para o Webhook
@webhook_bp.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    payload: Dict[str, Any] | None = request.json
    logger.info(f"Webhook recebido: {payload}")

    if not payload:
        return jsonify({"error": "no payload"}), 400

    json, status, phone_number = validators.extract_and_validate_phone(payload)

    if phone_number is None:
        return json, status

    try:
        # Usa o executor customizado
        async_processor(phone_number, payload)
        logger.info(f"Processamento assíncrono iniciado para {phone_number}")
    except Exception as e:
        logger.error(f"Erro ao iniciar processamento assíncrono: {e}", exc_info=True)
        return jsonify({"error": "processing start failed"}), 500

    return json, status
