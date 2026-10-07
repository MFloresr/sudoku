from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from sudoku.demo import debe_reiniciarse, es_demo, preparar_demo

from .forms import EntrarForm, RecuperarForm, RegistroForm


class EntrarView(auth_views.LoginView):
    template_name = "cuentas/entrar.html"
    authentication_form = EntrarForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        # Quien entra a mano con la cuenta demo también la encuentra con partidas limpias
        usuario = form.get_user()
        if es_demo(usuario) and debe_reiniciarse(usuario):
            # preparar_demo cambia el hash de la contraseña: hay que entrar con el usuario que
            # devuelve, si no la sesión queda invalidada y se vuelve a pedir el login
            login(self.request, preparar_demo(), backend="cuentas.backends.EmailBackend")
            return redirect(self.get_success_url())
        return super().form_valid(form)


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


def demo(request):
    """Entra con la cuenta de demostración (se crea la primera vez que alguien la usa)."""
    usuario = get_user_model().objects.filter(email__iexact=settings.DEMO_EMAIL).first()
    if usuario is None or debe_reiniciarse(usuario):
        usuario = preparar_demo()
    login(request, usuario, backend="cuentas.backends.EmailBackend")
    return redirect("inicio")


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
