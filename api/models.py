from .model.user import Utilizador, Cidadao, PT
from .model.denuncia import Denuncia
from .model.analise import ResultadoAnalise
from .model.evidencia import Evidencia
from .model.configuracao import ConfiguracaoAPI
from .model.jurisdicao import ViaJurisdicao

# Export all models for convenience
__all__ = ['Utilizador', 'Cidadao', 'PT', 'Denuncia', 'ResultadoAnalise', 'Evidencia', 'ConfiguracaoAPI', 'ViaJurisdicao']
