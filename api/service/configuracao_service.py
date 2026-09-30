from api.model.configuracao import ConfiguracaoAPI


class ConfiguracaoService:

    @staticmethod
    def listar():
        return ConfiguracaoAPI.objects.all().order_by("chave")

    @staticmethod
    def obter_valor(chave, default=None):
        try:
            config = ConfiguracaoAPI.objects.get(chave=chave)
            valor = config.get_valor()
            # Credenciais coladas num campo de texto trazem muitas vezes
            # espaços/quebras de linha nas pontas (ex: "\nESHOP"), que o
            # fornecedor recusa.
            return valor.strip() if isinstance(valor, str) else valor
        except ConfiguracaoAPI.DoesNotExist:
            return default

    @staticmethod
    def definir(chave, valor, publica=False, descricao=""):
        config, _ = ConfiguracaoAPI.objects.update_or_create(
            chave=chave,
            defaults={"publica": publica, "descricao": descricao},
        )
        config.set_valor(valor.strip() if isinstance(valor, str) else valor)
        config.save()
        return config

    @staticmethod
    def apagar(chave):
        ConfiguracaoAPI.objects.filter(chave=chave).delete()

    @staticmethod
    def listar_publicas():
        return {
            c.chave: c.get_valor()
            for c in ConfiguracaoAPI.objects.filter(publica=True)
        }
