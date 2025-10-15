import base64
from config import Config
from message import Message
from contentItem import ContentItem
from whatsappMessage import WhatsappMessage
from openaiIntegration import OpenaiIntegration
from evolutionIntegration import EvolutionIntegration
from flask import Flask, request, jsonify
from typing import Any, Literal, Optional, overload
import logging
import os

# Configurações do Flask e logging
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger: logging.Logger = logging.getLogger(__name__)

ACCEPTABLE_TYPES = Literal[
    "conversation", "audioMessage", "imageMessage", "documentMessage"
]


# Funções auxiliares
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
                        media_type = mimetype
                    else:
                        media_type = "document"

                    # Descriptografa e obtém URL pública
                    public_url: str | None = media_type
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
                        text_of_audio: str = ""
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

    try:
        if not payload:
            return jsonify({"status": "error", "message": "Requisição vazia"}), 400

        telefone: str = get_number(payload["data"]["key"].get("remoteJid", ""))

        if (
            telefone in Config.AUTHORIZED_NUMBERS
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
            message: Message = process_input(type=message_type, payload=payload)

            # Cria a mensagem do Whatsapp
            zapMessage: WhatsappMessage = WhatsappMessage(
                to_number=telefone,
                message=message,
            )
            logger.info(
                f"Mensagem recebida de {telefone} com {len(message.content)} {'item' if len(message.content) <= 1 else 'itens'} de conteúdo"
            )

            # Adiciona ao histórico
            zapMessage.add_to_history_DB()

            # Integrações
            openAI: OpenaiIntegration = OpenaiIntegration()
            evolutionAPI: EvolutionIntegration = EvolutionIntegration()

            try:
                openAI.create_response(zapMessage)
            except Exception:
                return (
                    jsonify({"status": "error", "message": "Erro ao criar mensagem"}),
                    500,
                )

            try:
                evolutionAPI.send_message(zapMessage)
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
                f"Número não autorizado ou mensagem enviada por si mesmo: {telefone}"
            )
            if telefone in Config.AUTHORIZED_NUMBERS:
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
        logger.error(f"Erro geral no webhook: {e}")
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
    os.makedirs("static", exist_ok=True)
    app.run(host="0.0.0.0", port=80, debug=False)
