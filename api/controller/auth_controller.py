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