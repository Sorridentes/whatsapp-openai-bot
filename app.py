from flask import Flask, request, jsonify
from typing import Any, Literal
import logging
import asyncio
import threading
import signal
from config import Config
from batch_processor import batch_processor
from concurrent.futures import ThreadPoolExecutor
from threadPoolExecutor import async_executor
import sys

# Configurações do Flask e logging
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt=r"%d-%m-%Y %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app_debug.log"),  # SALVA EM ARQUIVO TAMBÉM
    ],
)
logger: logging.Logger = logging.getLogger(__name__)

ACCEPTABLE_TYPES = Literal[
    "conversation", "audioMessage", "imageMessage", "documentMessage"
]


# Funções auxiliares
thread_executor = ThreadPoolExecutor(max_workers=10)


# Variável global para controlar se o monitor já foi iniciado
_monitor_started = False
_shutdown_event = asyncio.Event()


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
        async_executor.submit(process_message_async, phone_number, payload)

        # Opcional: você pode aguardar o resultado se necessário
        # future.result(timeout=30)

        logger.info(f"Mensagem enviada para processamento: {phone_number}")

    except Exception as e:
        logger.error(f"Erro ao submeter mensagem para processamento: {e}")


# Função assíncrona que será executada
async def process_message_async(phone_number: str, payload: dict[str, Any]):
    """Processa uma mensagem de forma assíncrona"""
    try:
        await batch_processor.add_message(phone_number, payload)
        logger.info(f"Mensagem processada com sucesso: {phone_number}")
    except Exception as e:
        logger.error(f"Erro no processamento assíncrono para {phone_number}: {e}")
        raise


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

    if not "s.whatsapp.net" in raw_jid:
        logger.warning("Messagem não vem do privado")
        return jsonify({"status": "skipped", "message": "Número não é do privado"}), 200

    phone_number = get_number(raw_jid)

    if not (
        phone_number in Config.AUTHORIZED_NUMBERS
        and not payload["data"]["key"]["fromMe"]
    ):
        logger.warning(f"Número não autorizado: {phone_number}")
        return jsonify({"status": "skipped", "message": "Número não autorizado"}), 200

    try:
        # Usa o executor customizado
        async_processor(phone_number, payload)
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
@app.route("/static/<path:filename>")
def serve_static(filename: str):
    return app.send_static_file(filename)


async def main():
    """Função principal assíncrona"""
    try:
        # Inicia o monitor
        await start_batch_monitor()

        # Inicia o Flask com Waitress
        from waitress import serve

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
        logger.error(f"Erro não esperado: {e}")
    finally:
        logger.info("Aplicação finalizada")
