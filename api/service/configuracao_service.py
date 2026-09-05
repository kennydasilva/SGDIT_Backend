from api.model.configuracao import ConfiguracaoAPI


class ConfiguracaoService:

    @staticmethod
    def listar():
        return ConfiguracaoAPI.objects.all().order_by("chave")

    @staticmethod
    def obter_valor(chave, default=None):
        try:
            config = ConfiguracaoAPI.objects.get(chave=chave)
            return config.get_valor()
        except ConfiguracaoAPI.DoesNotExist:
            return default

    @staticmethod
    def definir(chave, valor, publica=False, descricao=""):
        config, _ = ConfiguracaoAPI.objects.update_or_create(
            chave=chave,
            defaults={"publica": publica, "descricao": descricao},
        )
        config.set_valor(valor)
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
