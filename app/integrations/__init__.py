from app.integrations.evolutionIntegration import EvolutionIntegration
from app.integrations.openaiIntegration import OpenaiIntegration

# Instâncias globais
clientAI: OpenaiIntegration = OpenaiIntegration()
clientEvolution: EvolutionIntegration = EvolutionIntegration()
