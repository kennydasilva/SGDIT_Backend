from api.model.user import Utilizador,PT
#@kenny dasilva
#Servico de gestao de policias de transito (PTs)
#Responsabilidades: Ser
#1. Criar PTs
#2. Listar PTs
#3. Obter detalhes de um PT
#4. Actualizar detalhes de um PT
#5. Apagar um PT
class PTService:

    @staticmethod
    def criar_pt(nome, email, password, numero_agente, localizacao):

        utilizador =Utilizador.objects.create_user(
            username=email,
            email=email,
            password=password,
            nome=nome,
            role="PT"
        )

        pt= PT.objects.create(
            utilizador=utilizador,
            numero_agente=numero_agente,
            localizacao=localizacao
        )

        return pt
    
    @staticmethod
    def listar_pts():

        return PT.objects.all()
    
    @staticmethod
    def obter_pt(pt_id):

        return PT.objects.get(id=pt_id)
    
    @staticmethod
    def actualizar_pt(pt_id, nome=None, numero_agente=None, localizacao=None):

        pt=PT.objects.get(id=pt_id)

        if nome:
            pt.utilizador.nome=nome
            pt.utilizador.save()

        if numero_agente:
            pt.numero_agente=numero_agente
            pt.save()

        if localizacao:
            pt.localizacao=localizacao
            pt.save()

        return pt
    

    @staticmethod
    def apagar_pt(pt_id):

        pt=PT.objects.get(id=pt_id)

        pt.utilizador.delete()

        return True