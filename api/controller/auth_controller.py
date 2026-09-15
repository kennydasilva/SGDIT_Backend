from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api.service.auth_service import AuthService
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi



class LoginController(APIView):

    authentication_classes=[]
    permission_classes=[]

    @swagger_auto_schema(
        operation_description="Login do utilizador",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
            },
        )
    )

    def post(self, request):

        email=request.data.get("email")
        password=request.data.get("password")

        user=AuthService.login(email, password)

        if not user:
            return Response(
                {"error": "Credenciais invalidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh=RefreshToken.for_user(user)

        return Response({

            "access": str(refresh.access_token),
            "refresh": str(refresh),

            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
        })


class PasswordResetRequestController(APIView):

    authentication_classes=[]
    permission_classes=[]

    @swagger_auto_schema(
        operation_description="Solicitar recuperação de senha",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING),
            },
        )
    )
    def post(self, request):

        email = request.data.get("email")

        if not email:
            return Response(
                {"error": "Email é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )

        AuthService.solicitar_reset_senha(email)

        return Response(
            {"message": "Se o email existir, um link de recuperação foi enviado"}
        )


class PasswordResetConfirmController(APIView):

    authentication_classes=[]
    permission_classes=[]

    @swagger_auto_schema(
        operation_description="Confirmar recuperação de senha",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "uid": openapi.Schema(type=openapi.TYPE_STRING),
                "token": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
            },
        )
    )
    def post(self, request):

        uid = request.data.get("uid")
        token = request.data.get("token")
        password = request.data.get("password")

        if not uid or not token or not password:
            return Response(
                {"error": "uid, token e password são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST
            )

        sucesso = AuthService.confirmar_reset_senha(uid, token, password)

        if not sucesso:
            return Response(
                {"error": "Link inválido ou expirado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"message": "Senha redefinida com sucesso"})


class FcmTokenController(APIView):
    """
    Regista o token de push (Firebase Cloud Messaging) do dispositivo/browser
    onde o utilizador autenticado tem sessão aberta. Usado sobretudo por
    Admins, para receberem a notificação de acidente de viação na
    jurisdição do seu posto assim que abrem a dashboard e autorizam
    notificações - sem isto, a denúncia continua a ser criada, só não há
    push a avisar em tempo real.
    """

    @swagger_auto_schema(
        operation_description="Registar/actualizar o token FCM do utilizador autenticado",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "fcm_token": openapi.Schema(type=openapi.TYPE_STRING),
            },
        )
    )
    def patch(self, request):

        fcm_token = request.data.get("fcm_token")

        if not fcm_token:
            return Response(
                {"error": "fcm_token é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.fcm_token = fcm_token
        request.user.save(update_fields=["fcm_token"])

        return Response({"message": "Token registado"})