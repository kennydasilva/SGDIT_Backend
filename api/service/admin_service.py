from api.model.user import Utilizador,Admin

class AdminService:

    @staticmethod
    def criar_admin(nome, email, password, posto):

        utilizador =Utilizador.objects.create_user(
            username=email,
            email=email,
            password=password,
            nome=nome,
            role="ADMIN"
        )

        admin= Admin.objects.create(
            utilizador=utilizador,
            posto=posto
        )

        return admin
    
    @staticmethod
    def listar_admins():

        return Admin.objects.all()
    
    @staticmethod
    def obter_admin(admin_id):

        return Admin.objects.get(id=admin_id)
    
    @staticmethod
    def actualizar_admin(admin_id, nome=None, posto=None):

        admin=Admin.objects.get(id=admin_id)

        if nome:
            admin.utilizador.nome=nome
            admin.utilizador.save()

        if posto:
            admin.posto=posto
            admin.save()

        return admin
    

    @staticmethod
    def apagar_admin(admin_id):

        admin=Admin.objects.get(id=admin_id)

        admin.utilizador.delete()

        return True