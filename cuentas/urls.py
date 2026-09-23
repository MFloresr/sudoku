from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("entrar/", views.EntrarView.as_view(), name="entrar"),
    path("registro/", views.registro, name="registro"),
    path("salir/", auth_views.LogoutView.as_view(), name="salir"),
    path("recuperar/", views.RecuperarView.as_view(), name="recuperar"),
    path("recuperar/enviado/", views.RecuperarEnviadoView.as_view(), name="recuperar_enviado"),
    path("recuperar/<uidb64>/<token>/", views.NuevaClaveView.as_view(), name="password_reset_confirm"),
    path("recuperar/hecho/", views.ClaveCambiadaView.as_view(), name="clave_cambiada"),
]
