from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm


class EntrarForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True, "placeholder": "nombre@correo.com"}),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "placeholder": "Tu contraseña"}),
    )
    error_messages = {
        "invalid_login": "El email o la contraseña no son correctos.",
        "inactive": "Esta cuenta está desactivada.",
    }


class RegistroForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre",
        max_length=40,
        widget=forms.TextInput(attrs={"autocomplete": "given-name", "placeholder": "Cómo quieres que te llamemos"}),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "nombre@correo.com"}),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Mínimo 8 caracteres"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya hay una cuenta con este email. ¿Quieres entrar?")
        return email

    def clean(self):
        datos = super().clean()
        password = datos.get("password")
        if password:
            usuario = get_user_model()(username=datos.get("email", ""), email=datos.get("email", ""), first_name=datos.get("nombre", ""))
            try:
                password_validation.validate_password(password, usuario)
            except forms.ValidationError as e:
                self.add_error("password", e)
        return datos

    def save(self):
        User = get_user_model()
        email = self.cleaned_data["email"]
        return User.objects.create_user(
            username=email[:150],
            email=email,
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["nombre"].strip(),
        )


class RecuperarForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "nombre@correo.com"}),
    )
