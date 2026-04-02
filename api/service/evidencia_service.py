from api.model.evidencia import Evidencia
from api.model.denuncia import Denuncia

class EvidenciaService:

    @staticmethod
    def criar_evidencia(denuncia_id, ficheiro):

        denuncia=Denuncia.objects.get(id=denuncia_id)

        if hasattr(denuncia, "evidencia"):
            raise ValueError("Denuncia ja possui evidencia")
        
        evidencia=Evidencia.objects.create(
            denuncia=denuncia,
            caminho_ficheiro=ficheiro
        )

        return evidencia
    
    @staticmethod
    def obter_evidencia(denuncia_id):
        try:
            return Evidencia.objects.get(denuncia_id=denuncia_id)
        except Evidencia.DoesNotExist:
            return None