from django.contrib.auth import authenticate

class AuthService:

    @staticmethod
    def login(email, password):

        user=authenticate(
            username=email,
            password=password
        )

        return user