from api.model.evidencia import Evidencia
from api.model.denuncia import Denuncia

class EvidenciaService:

    

    @staticmethod
    def criar_evidencia(denuncia, ficheiro):
        return Evidencia.objects.create(
            denuncia=denuncia,
            caminho_ficheiro=ficheiro
        )
    
    @staticmethod
    def obter_evidencia(denuncia_id):
        try:
            return Evidencia.objects.get(denuncia_id=denuncia_id)
        except Evidencia.DoesNotExist:
            return None