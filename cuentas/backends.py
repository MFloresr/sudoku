from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Permite entrar con el email (sin distinguir mayúsculas) además del nombre de usuario."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        User = get_user_model()
        user = (
            User.objects.filter(email__iexact=username.strip()).order_by("id").first()
            or User.objects.filter(username=username).first()
        )
        if user is None:
            User().set_password(password)  # mismo coste de tiempo aunque no exista
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
