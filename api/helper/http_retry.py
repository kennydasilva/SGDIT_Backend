import logging
import time

logger = logging.getLogger(__name__)


def com_retry(func, tentativas=3, espera_segundos=1.5, nome="pedido externo"):
    """
    Corre `func()` até `tentativas` vezes, com pequena espera entre cada
    tentativa - serviços públicos como o Nominatim/Overpass falham de forma
    transitória (timeout, 5xx, rate-limit) com alguma frequência; a maioria
    dos casos resolve-se só por tentar outra vez.

    Devolve o resultado da 1ª tentativa bem sucedida, ou levanta a última
    excepção se todas falharem (quem chama decide o que fazer - ex:
    devolver 503 em vez de rebentar).
    """
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            return func()
        except Exception as erro:
            ultimo_erro = erro
            logger.warning("%s falhou (tentativa %d/%d): %s", nome, tentativa, tentativas, erro)
            if tentativa < tentativas:
                time.sleep(espera_segundos * tentativa)

    raise ultimo_erro
