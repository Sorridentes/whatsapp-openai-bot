import base64
from config import Config
from message import Message
from contentItem import ContentItem
from whatsappMessage import WhatsappMessage
from decrypt import decryptByLink
from openaiIntegration import clientAI
from evolutionIntegration import clientEvolution
from flask import Flask, request, jsonify
from typing import Any, Literal, Optional, overload
from database import mongo_db, redis_queue
from messageProcessor import message_processor
import logging
import asyncio
import os

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
def async_processor(message: Message):
    """Executa o processamento assíncrono em thread separada"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(message_processor.process_input(message))
    loop.close()

def get_number(strTelefone: Any) -> str:
    tel: str = strTelefone.split("@")[0]
    if len(tel) == 12:
        tel = tel[:3] + "9" + tel[4:]
        logger.info(f"Número ajustado para formato com 13 dígitos")

    logger.info(f"Número extraído: {tel}")
    return tel


def cleanup_file(file_path: str) -> None:
    """Remove arquivo temporário de forma segura"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Arquivo temporário removido: {file_path}")
    except Exception as e:
        logger.warning(f"Erro ao remover arquivo temporário {file_path}: {e}")
        raise e


@overload
def process_input(
    type: Literal["conversation"], payload: dict[str, Any]
) -> Message: ...


@overload
def process_input(
    type: Literal["audioMessage"], payload: dict[str, Any]
) -> Message: ...


@overload
def process_input(
    type: Literal["imageMessage"], payload: dict[str, Any]
) -> Message: ...


@overload
def process_input(
    type: Literal["documentMessage"], payload: dict[str, Any]
) -> Message: ...


def process_input(type: ACCEPTABLE_TYPES, payload: dict[str, Any]) -> Message:
    """
    Processa diferentes tipos de entrada do webhook e retorna uma variável Message
    """
    content_items: list[ContentItem] = []
    logger.info(f"Tipo da messagem recebida: {type}")

    try:
        if type == "conversation":
            # Mensagem de texto simples
            text: str = payload["data"]["message"].get("conversation", "")
            content_items.append(ContentItem(type="input_text", text=text))

        else:
            # Processa mídia (áudio, imagem, documento)
            message_data: dict[str, Any] = payload["data"]["message"].get(type, "")

            # Extrai informações da mídia
            media_url: Optional[str] = message_data.get("url")
            media_key: bytes = base64.b64decode(message_data.get("mediaKey", b""))
            mimetype: Optional[str] = message_data.get("mimetype")
            caption: Optional[str] = message_data.get("caption")

            if media_url and media_key:
                try:
                    # Determina o tipo da mídia para o decrypt
                    if type == "audioMessage":
                        media_type = "audio"
                    elif type == "imageMessage":
                        if mimetype:
                            media_type = mimetype
                        else:
                            media_type = "image"
                    else:
                        media_type = "document"

                    # Descriptografa e obtém URL pública
                    try:
                        public_url: str = decryptByLink(
                            link=media_url, mediaKey=media_key, mediaType=media_type
                        )
                    except Exception as e:
                        raise e
                    logger.info(
                        f"Mídia descriptografada e disponível em : {public_url}"
                    )

                    # Adiciona o item de conteúdo apropriado
                    if type == "imageMessage":
                        # Se houver caption, adiciona como texto também
                        if caption:
                            content_items.append(
                                ContentItem(type="input_text", text=caption)
                            )

                        content_items.append(
                            ContentItem(type="input_image", image_url=public_url)
                        )

                    elif type == "audioMessage":
                        # Transforma o audio em texto
                        text_of_audio: str = clientAI.transcribe_audio(public_url)
                        content_items.append(
                            ContentItem(type="input_text", text=text_of_audio)
                        )

                    elif type == "documentMessage":
                        if caption:
                            content_items.append(
                                ContentItem(type="input_text", text=caption)
                            )

                        content_items.append(
                            ContentItem(type="input_file", file_url=public_url)
                        )
                except Exception as e:
                    logger.error(f"Erro ao processar mídia: {e}")
                    raise e
        message = Message(role="user", content=content_items)
        return message

    except Exception as e:
        logger.error(f"Erro geral no process_input: {e}")
        raise e


# Mapeamento das rotas
@app.route("/v1/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    payload: dict[str, Any] | None = request.json
    logger.info(f"Webhook recebido: {payload}")
    # logger.info(f"Webhook recebido - Tipo: {payload.get('data', {}).get('messageType', 'unkown') if payloaad else 'no payload'}"")
    
    # Recupera todas as mensagens pendentes
    try:
        if not payload:
            return jsonify({"status": "error", "message": "Requisição vazia"}), 400

        phone: str = get_number(payload["data"]["key"].get("remoteJid", ""))

        if (
            phone in Config.AUTHORIZED_NUMBERS
            and not payload["data"]["key"]["fromMe"]
        ):
            try:
                message_type: ACCEPTABLE_TYPES = payload["data"].get(
                    "messageType", "unknown"
                )
            except TypeError as e:
                logger.warning(f"Tipo de messagem não suportado: {e}")
                return (
                    jsonify(
                        {
                            "status": "skipped",
                            "message": "Tipo de messagemnão suportado",
                        }
                    ),
                    200,
                )

            # Processa a entrada
            try:
                message: Message = process_input(type=message_type, payload=payload)
            except Exception as e:
                logger.error("Erro ao processar entrada", exc_info=True)
                return jsonify(
                    {
                        "status": "error",
                        "message": "Erro ao processar entrada do webhook",
                    }
                )

            # Cria a mensagem do Whatsapp
            zapMessage: WhatsappMessage = WhatsappMessage(
                to_number=phone,
                message=message,
            )
            logger.info(
                f"Mensagem recebida de {phone} com {len(message.content)} {'item' if len(message.content) <= 1 else 'itens'} de conteúdo"
            )

            # Adiciona ao histórico
            zapMessage.add_to_history_DB()

            try:
                clientAI.create_response(zapMessage)
            except Exception:
                return (
                    jsonify({"status": "error", "message": "Erro ao criar mensagem"}),
                    500,
                )

            try:
                clientEvolution.send_message(zapMessage)
            except Exception:
                return (
                    jsonify({"status": "error", "message": "Erro ao enviar mensagem"}),
                    500,
                )

            # Adiciona resposta ao histórico
            zapMessage.add_to_history_DB()
            return jsonify({"status": "enviada"}), 200

        else:
            logger.warning(
                f"Número não autorizado ou mensagem enviada por si mesmo: {phone}"
            )
            if phone in Config.AUTHORIZED_NUMBERS:
                return (
                    jsonify({"status": "error", "message": "Número não autorizado"}),
                    403,
                )
            else:
                return (
                    jsonify(
                        {
                            "status": "skipped",
                            "message": "Mensagem enviada por si mesmo",
                        }
                    ),
                    200,
                )
    except Exception as e:
        logger.error(f"Erro geral no webhook", exc_info=True)
        return jsonify({"status": "error", "message": "Erro interno do servidor"}), 500


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
    app.run(host="0.0.0.0", port=80, debug=False)
