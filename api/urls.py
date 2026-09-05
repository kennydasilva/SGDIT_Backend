from django.urls import path
from rest_framework.routers import DefaultRouter

from api.controller.auth_controller import LoginController, PasswordResetRequestController, PasswordResetConfirmController
from api.controller.cidadao_controller import CidadaoUserViewSet, RegistarCidadaoController
from api.controller.admin_controller import AdminController
from api.controller.denucia_controller import DenunciaViewSet
from api.controller.pt_controller import PtViewSet, PtUserViewSet
from api.controller.superadmin_controller import SuperAdminViewSet
from api.controller.configuracao_controller import ConfiguracaoPublicaController
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r"pts", PtViewSet, basename="pts")
router.register(r"pts/user", PtUserViewSet, basename="pts-user")
router.register(r"denuncias", DenunciaViewSet, basename="denuncias")
router.register(r"cidadao/user", CidadaoUserViewSet, basename="cidadao-users")
router.register(r"", SuperAdminViewSet, basename="superadmin")

urlpatterns = [
    path("login/", LoginController.as_view()),
    path("password-reset/", PasswordResetRequestController.as_view()),
    path("password-reset/confirm/", PasswordResetConfirmController.as_view()),
    path("cidadaos/registrar/", RegistarCidadaoController.as_view()),
    path("admins/", AdminController.as_view()),
    path("config/publica/", ConfiguracaoPublicaController.as_view()),

]

urlpatterns += router.urls
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)