from django.core.management.base import BaseCommand

from api.model.evidencia import Evidencia
from api.service.assinatura_video_service import AssinaturaVideoService


class Command(BaseCommand):
    help = (
        "Calcula a assinatura visual dos vídeos já existentes (sem assinatura), "
        "para vídeos novos semelhantes a eles serem ligados. Não liga nem altera "
        "denúncias existentes."
    )

    def handle(self, *args, **options):
        feitas, falhas = 0, 0
        for evidencia in Evidencia.objects.filter(assinaturas__isnull=True).distinct():
            nome = evidencia.caminho_ficheiro.name.lower() if evidencia.caminho_ficheiro else ""
            if not nome.endswith((".mp4", ".avi", ".mov")):
                continue
            try:
                hashes = AssinaturaVideoService.calcular(evidencia.caminho_ficheiro.path)
                AssinaturaVideoService.guardar(evidencia, hashes)
                feitas += 1
            except Exception as e:
                falhas += 1
                self.stderr.write(f"Evidência {evidencia.id}: {e}")
        self.stdout.write(self.style.SUCCESS(f"Assinaturas calculadas: {feitas} (falhas: {falhas})"))
