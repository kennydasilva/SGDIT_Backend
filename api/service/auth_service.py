import re
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from api.model.user import Utilizador

token_generator = PasswordResetTokenGenerator()


class AuthService:

    @staticmethod
    def login(email, password):

        user=authenticate(
            username=email,
            password=password
        )

        return user

    @staticmethod
    def solicitar_reset_senha(email):

        try:
            user = Utilizador.objects.get(email=email)
        except Utilizador.DoesNotExist:
            return

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        link = f"{settings.FRONTEND_URL}/redefinir-senha/{uid}/{token}"

        send_mail(
            subject="Recuperação de senha - SGDIT",
            message=f"Para redefinir a sua senha, aceda ao link: {link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

    @staticmethod
    def confirmar_reset_senha(uidb64, token, nova_password):

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = Utilizador.objects.get(pk=uid)
        except (Utilizador.DoesNotExist, ValueError, TypeError, OverflowError):
            return False

        if not token_generator.check_token(user, token):
            return False

        user.set_password(nova_password)
        user.save()
        return True

    @staticmethod
    def alterar_senha(user, senha_atual, nova_senha):
        """Devolve a mensagem de erro, ou None se a senha foi alterada."""

        if not user.check_password(senha_atual):
            return "A senha actual está incorrecta"

        # A mesma regra do registo e da redefinição (validada no frontend).
        if (
            len(nova_senha) < 8
            or not re.search(r"[a-z]", nova_senha)
            or not re.search(r"[A-Z]", nova_senha)
            or not re.search(r"\d", nova_senha)
        ):
            return "A nova senha deve ter no mínimo 8 caracteres, com maiúscula, minúscula e número"

        if senha_atual == nova_senha:
            return "A nova senha tem de ser diferente da actual"

        user.set_password(nova_senha)
        user.save()
        return None
