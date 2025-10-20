import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Configuração da OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini-2025-04-14")
    OPENAI_PROMPT_ID: str = os.getenv("OPENAI_PROMPT_ID", "")
    PROMPT_ID_VERSION: str = os.getenv("PROMPT_ID_VERSION", "1")

    # Configuração da EvolutionAPI
    EVOLUTION_APIKEY: str = os.getenv("EVOLUTION_APIKEY", "")
    EVOLUTION_SERVER_URL: str = os.getenv("EVOLUTION_SERVER_URL", "")
    EVOLUTION_NAME_INSTANCE: str = os.getenv("EVOLUTION_NAME_INSTANCE", "")

    # Configuração do Ngrok
    NGROK_URL: str = os.getenv("NGROK_URL", ".")

    # Configuração do MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGO_INITDB_DATABASE: str = os.getenv("MONGO_INITDB_DATABASE", "whatsapp_bot")

    # Configuração do Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    BATCH_PROCESSING_DELAY: int = int(os.getenv("BATCH_PROCESSING_DELAY", "3"))

    # Autenticações
    SHUTDOWN_API_KEY: str = os.getenv("SHUTDOWN_API_KEY", "123")

    # Números autorizados a usar o bot
    AUTHORIZED_NUMBERS: list[str] = (
        os.getenv("AUTHORIZED_NUMBERS", "").split(",")
        if os.getenv("AUTHORIZED_NUMBERS")
        else []
    )
