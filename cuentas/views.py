from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import EntrarForm, RecuperarForm, RegistroForm


class EntrarView(auth_views.LoginView):
    template_name = "cuentas/entrar.html"
    authentication_form = EntrarForm
    redirect_authenticated_user = True


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario, backend="cuentas.backends.EmailBackend")
        messages.success(request, f"¡Bienvenido, {usuario.first_name}! Elige una dificultad para empezar.")
        return redirect("inicio")
    return render(request, "cuentas/registro.html", {"form": form})


class RecuperarView(auth_views.PasswordResetView):
    template_name = "cuentas/recuperar.html"
    form_class = RecuperarForm
    email_template_name = "cuentas/email_recuperar.txt"
    subject_template_name = "cuentas/email_recuperar_asunto.txt"
    success_url = reverse_lazy("recuperar_enviado")


class RecuperarEnviadoView(auth_views.PasswordResetDoneView):
    template_name = "cuentas/recuperar_enviado.html"


class NuevaClaveView(auth_views.PasswordResetConfirmView):
    template_name = "cuentas/nueva_clave.html"
    success_url = reverse_lazy("clave_cambiada")


class ClaveCambiadaView(auth_views.PasswordResetCompleteView):
    template_name = "cuentas/clave_cambiada.html"
