class Pessoa:
    def __init__(self, telefone: str, mensagem: str, conversition_history: list = []):
        self.telefone: str = telefone
        self.mensagem: str = mensagem
        self.conversition_history: list[str] = conversition_history
