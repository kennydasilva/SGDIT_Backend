

from api.model.user import Cidadao, Utilizador


class CidadaoService:

    @staticmethod
    def registar_cidadao(nome, email, password, numero=None):

        utilizador = Utilizador.objects.create_user(
            username=email,
            email=email,
            password=password,
            nome=nome,
            numero=numero,
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


    @staticmethod
    def actualizar_cidadao(cidadao_id, nome=None, numero=None):

        cidadao = Cidadao.objects.get(utilizador__id=cidadao_id)

        if nome:
            cidadao.utilizador.nome = nome

        if numero:
            cidadao.utilizador.numero = numero

        cidadao.utilizador.save()
        return cidadao


    @staticmethod
    def listar_cidadaos():

        return Cidadao.objects.all()


