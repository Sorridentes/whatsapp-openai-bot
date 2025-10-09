import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Configuração da OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL")
    
    # Configuração da EvolutionAPI
    EVOLUTION_APIKEY: str = os.getenv("EVOLUTION_APIKEY")
    EVOLUTION_SERVER_URL: str = os.getenv("EVOLUTION_SERVER_URL")
    EVOLUTION_NAME_INSTANCE: str = os.getenv("EVOLUTION_NAME_INSTANCE")
    
    # Números autorizados a usar o bot
    AUTHORIZED_NUMBERS: list = os.getenv("AUTHORIZED_NUMBERS", "").split(",") if os.getenv("AUTHORIZED_NUMBERS") else []