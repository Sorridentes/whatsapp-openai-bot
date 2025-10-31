from flask import Blueprint, render_template
import logging


logger: logging.Logger = logging.getLogger(__name__)

# Cria um Blueprint para webhooks
main_bp = Blueprint("main", __name__)


# Rota principal
@main_bp.route("/")
def home():
    return render_template("index.html")


# Rota para servir arquivos estáticos (necessário para o ngrok)
@main_bp.route("/static/<path:filename>")
def serve_static(filename: str):
    return main_bp.send_static_file(filename)
