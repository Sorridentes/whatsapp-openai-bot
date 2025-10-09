import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Configuração da OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL")
    
    # Configuração da EvolutionAPI
    APIKEY: str = os.getenv("APIKEY")
    SERVER_URL: str = os.getenv("SERVER_URL")
    NAME_INSTANCE: str = os.getenv("NAME_INSTANCE")
    
    # Números autorizados a usar o bot
    AUTHORIZED_NUMBERS: list = os.getenv("AUTHORIZED_NUMBERS", "").split(",") if os.getenv("AUTHORIZED_NUMBERS") else []