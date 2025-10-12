from config import Config
from whatsappMessage import WhatsappMessage
from openaiIntegration import OpenaiIntegration
from evolutionIntegration import EvolutionIntegration
from flask import Flask, request, jsonify
from typing import Any
import logging

# Configurações do Flask e logging
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger: logging.Logger = logging.getLogger(__name__)

# Funções auxiliares
def get_number(strTelefone: Any) -> str:  
    tel: str = strTelefone.split("@")[0]
    if len(tel) == 12:
        tel = tel[:3] + "9" + tel[4:]
        logger.info(f"Número ajustado para formato com 13 dígitos")
    
    logger.info(f"Número extraído: {tel}")
    return tel

# Mapeamento das rotas
@app.route('/v1/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    payload:  dict[str, Any] | None = request.json
    logger.info(f"Webhook recebido: {payload}")

    if not payload:
        return jsonify({"status": "error", "message": "Requisição vazia"}), 400
    
    telefone: str = get_number(payload['data']['key'].get('remoteJid', ''))
    if telefone in Config.AUTHORIZED_NUMBERS and not payload['data']['key']['fromMe']:
        openAI: OpenaiIntegration = OpenaiIntegration()
        evolutionAPI: EvolutionIntegration = EvolutionIntegration()
        context: str = payload['data']['message']['conversation']
        message: WhatsappMessage = WhatsappMessage(
            to_number= telefone,
            message_text= context,
        )
        message.add_to_history({
            "role": "user", 
            "content": [
                {
                    "type": "input_text", 
                    "text": context
                }
            ]
        })
        logger.info(f"Mensagem recebida de {telefone}: {context}")
        try:
            responseAI: str = openAI.create_response(message)
        except Exception:
            return jsonify({"status": "error", "message": "Erro ao criar mensagem"}), 500
        else:
            message.message_text = responseAI
            try:
                evolutionAPI.send_message(message)
            except Exception:
                return jsonify({"status": "error", "message": "Erro ao enviar mensagem"}), 500
        return {"status": "enviada"}, 200
    else:
        logger.warning(f"Número não autorizado ou mensagem enviada por si mesmo: {telefone}")
        if telefone in Config.AUTHORIZED_NUMBERS:
            return jsonify({"status": "error", "message": "Número não autorizado"}), 403
        else:
            return jsonify({"status": "skipped", "message": "Mensagem enviada por si mesmo"}), 200
            

@app.route('/')
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)