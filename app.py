from database import redis_queue
from flask import Flask, request, jsonify
from typing import Any, Literal
from messageProcessor import message_processor
import logging
import asyncio
import threading

# Configurações do Flask e logging
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt=r"%d-%m-%Y %H:%M:%S",
)
logger: logging.Logger = logging.getLogger(__name__)

ACCEPTABLE_TYPES = Literal[
    "conversation", "audioMessage", "imageMessage", "documentMessage"
]


# Funções auxiliares
def async_processor(type: ACCEPTABLE_TYPES, phone_number: str):
    """Executa o processamento assíncrono em thread separada"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        message_processor.process_phone_messages(type, phone_number)
    )
    loop.close()


def get_number(strTelefone: Any) -> str:
    tel: str = strTelefone.split("@")[0]
    if len(tel) == 12:
        tel = tel[:3] + "9" + tel[4:]
        logger.info(f"Número ajustado para formato com 13 dígitos")

    logger.info(f"Número extraído: {tel}")
    return tel


# Mapeamento das rotas
@app.route("/v1/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    payload: dict[str, Any] | None = request.json
    logger.info(f"Webhook recebido: {payload}")

    if not payload:
        return jsonify({"error": "no payload"}), 400

    raw_jid = payload["data"]["key"].get("remoteJid", "")
    if not raw_jid:
        logger.warning("Não foi possível extrair número do payload")
        return jsonify({"error": "phone not found"}), 400

    phone_number = get_number(raw_jid)
    msg_type: ACCEPTABLE_TYPES = payload["data"].get("messageType")

    # salva a mensagem crua na fila Redis (será desserializada pelo messageProcessor)
    try:
        redis_queue.add_message(phone_number, payload)
        logger.info(f"Mensagem salva no Redis para {phone_number}")
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem no Redis: {e}", exc_info=True)
        return jsonify({"error": "redis error"}), 500

    # dispara o processamento em background
    try:
        thread = threading.Thread(
            target=async_processor, args=(msg_type, phone_number), daemon=True
        )
        thread.start()
        logger.info(f"Processamento assíncrono iniciado para {phone_number}")
    except Exception as e:
        logger.error(f"Erro ao iniciar processamento assíncrono: {e}", exc_info=True)
        return jsonify({"error": "processing start failed"}), 500

    return jsonify({"status": "queued", "phone": phone_number}), 202


@app.route("/")
def home():
    return """
    <html>
        <head>
            <title>Bem-vindo</title>
            <style>
                body {
                    background: #f7fafc;
                    font-family: Arial, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                }
                .container {
                    background: #fff;
                    padding: 2rem 3rem;
                    border-radius: 12px;
                    box-shadow: 0 2px 16px rgba(0,0,0,0.08);
                    text-align: center;
                }
                h1 {
                    color: #2d3748;
                    margin-bottom: 0.5rem;
                }
                p {
                    color: #4a5568;
                    font-size: 1.1rem;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Bem-vindo ao Meu Site!</h1>
                <p>Este site integra a <b>Evolution API</b> e a <b>OpenAI</b> para automação inteligente no WhatsApp.</p>
            </div>
        </body>
    </html>
    """


# Rota para servir arquivos estáticos (necessário para o ngrok)
@app.route("/stattic/<path:filename>")
def serve_static(filename: str):
    return app.send_static_file(filename)


if __name__ == "__main__":
    # Garante que a pasta statix existe
    app.run(host="0.0.0.0", port=8080, debug=False)
