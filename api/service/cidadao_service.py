from api.model.user import Cidadao, Utilizador


class CidadaoService:

    @staticmethod
    def registar_cidadao(nome, email, password):

        utilizador = Utilizador.objects.create_user(
            username=email,
            email=email,
            password=password,
            nome=nome,
            role="CIDADAO"
        )

        cidadao = Cidadao.objects.create(
            utilizador=utilizador
        )

        return cidadao
    

    @staticmethod
    def obter_cidadaoById(id):

        cidadao=Cidadao.objects.get(utilizador__id=id)

        return cidadao



