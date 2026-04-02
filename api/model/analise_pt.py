from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from .denuncia import Denuncia
from .user import PT

class Analise(models.Model):
    denuncia = models.ForeignKey(Denuncia, on_delete=models.CASCADE)
    pt = models.ForeignKey(PT, on_delete=models.CASCADE)
    parecer = models.TextField()
    data = models.DateTimeField(auto_now_add=True)