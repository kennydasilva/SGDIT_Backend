from django.urls import path
from rest_framework.routers import DefaultRouter

from api.controller.auth_controller import LoginController
from api.controller.cidadao_controller import RegistarCidadaoController
from api.controller.admin_controller import AdminController
from api.controller.denucia_controller import DenunciaViewSet
from api.controller.pt_controller import PtViewSet
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r"pts", PtViewSet, basename="pts")
router.register(r"denuncias", DenunciaViewSet, basename="denuncias")

urlpatterns = [
    path("login/", LoginController.as_view()),
    path("cidadaos/registrar/", RegistarCidadaoController.as_view()),
    path("admins/", AdminController.as_view()),

]

urlpatterns += router.urls
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)