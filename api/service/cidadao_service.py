from api.model.user import Cidadao, Utilizador


class CidadaoService:

    @staticmethod
    def registar_cidadao(nome, email, password):

        Utilizador=Utilizador.objects.create_user(
            username=email,
            email=email,
            password=password,
            nome=nome,
            role="CIDADAO"
        )

        cidadao=Cidadao.objects.create(
            utilizador=Utilizador
        )   

        return cidadao