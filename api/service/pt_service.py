from api.model.user import Admin, Utilizador,PT
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
    def criar_pt(nome, email, password, numero_agente, localizacao, numero_utilizador_admin):

        utilizador =Utilizador.objects.create_user(
            username=email,
            email=email,
            password=password,
            nome=nome,
            role="PT"
        )

        admin=None
        try:
            admin = Admin.objects.get(utilizador_id=numero_utilizador_admin)
        except Admin.DoesNotExist:
           
            utilizador.delete()
            raise ValueError(
                f"Nenhum Admin encontrado para o utilizador_id {numero_utilizador_admin}"
            )


        pt= PT.objects.create(
            utilizador=utilizador,
            numero_agente=numero_agente,
            localizacao=localizacao,
            admin=admin
        )

        return pt
    
    @staticmethod
    def listar_pts():

        return PT.objects.all()
    
    @staticmethod
    def obter_pt(pt_id):
        

        return PT.objects.get(tilizador_id=pt_id)
    
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


    @staticmethod
    def listar_pts_por_admin(utilizador_id):
        admin=None

        try:
            admin = Admin.objects.get(utilizador_id=utilizador_id)
            
        except Admin.DoesNotExist:
            raise ValueError(
                f"Nenhum Admin encontrado para o utilizador_id {utilizador_id}"
            )
        
        return PT.objects.select_related("utilizador").filter(admin_id=admin.id)
    