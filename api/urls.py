from django.urls import path
from rest_framework.routers import DefaultRouter

from api.controller.auth_controller import LoginController
from api.controller.cidadao_controller import RegistarCidadaoController
from api.controller.admin_controller import AdminController
from api.controller.pt_controller import PtViewSet

router = DefaultRouter()
router.register(r"pts", PtViewSet, basename="pts")

urlpatterns = [
    path("login/", LoginController.as_view()),
    path("cidadaos/registrar/", RegistarCidadaoController.as_view()),
    path("admins/", AdminController.as_view()),
]

urlpatterns += router.urls