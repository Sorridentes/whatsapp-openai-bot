from flask import jsonify
from typing import Dict, Tuple, Any, Optional
import logging
from app.core.config import Config

logger: logging.Logger = logging.getLogger(__name__)


def extract_and_validate_phone(
    payload: Dict[str, Any],
) -> Tuple[Any, int, Optional[str]]:

    raw_jid = payload["data"]["key"].get("remoteJid", "")

    if not raw_jid:
        logger.warning("Não foi possível extrair número do payload")
        return jsonify({"error": "phone not found"}), 400, None

    if not "s.whatsapp.net" in raw_jid:
        logger.warning("Messagem não vem do privado")
        return (
            jsonify({"status": "skipped", "message": "Número não é do privado"}),
            200,
            None,
        )

    phone_number = _get_number(raw_jid)

    if not (
        phone_number in Config.AUTHORIZED_NUMBERS
        and not payload["data"]["key"]["fromMe"]
    ):
        logger.warning(f"Número não autorizado: {phone_number}")
        return (
            jsonify({"status": "skipped", "message": "Número não autorizado"}),
            200,
            None,
        )

    return (
        jsonify({"status": "queued", "phone": phone_number}),
        202,
        phone_number,
    )


def _get_number(strTelefone: Any) -> str:
    tel: str = strTelefone.split("@")[0]
    if len(tel) == 12:
        tel = tel[:3] + "9" + tel[4:]
        logger.info(f"Número ajustado para formato com 13 dígitos")

    logger.info(f"Número extraído: {tel}")
    return tel
