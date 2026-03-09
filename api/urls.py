from django.urls import path

from api.controller.auth_controller import LoginController
from api.controller.cidadao_controller import RegistarCidadaoController
from api.controller.admin_controller import AdminController


urlpatterns = [

    path(
        "login/",
        LoginController.as_view()
    ),

    path(
        "cidadaos/registrar/",
        RegistarCidadaoController.as_view()
    ),

    path(
        "admins/",
        AdminController.as_view()
    ),
]