from django.urls import path

from api.controllers.auth_controller import LoginController
from api.controllers.cidadao_controller import RegistrarCidadaoController
from api.controllers.admin_controller import AdminController


urlpatterns = [

    path(
        "auth/login/",
        LoginController.as_view()
    ),

    path(
        "cidadaos/registrar/",
        RegistrarCidadaoController.as_view()
    ),

    path(
        "admins/",
        AdminController.as_view()
    ),
]