from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse


class CuentasTests(TestCase):
    def test_registro_crea_usuario_y_entra(self):
        r = self.client.post(reverse("registro"), {"nombre": "Ana", "email": "Ana@Example.com", "password": "unaclave-larga-9"})
        self.assertRedirects(r, reverse("inicio"))
        u = User.objects.get()
        self.assertEqual((u.email, u.first_name), ("ana@example.com", "Ana"))
        self.assertEqual(self.client.get(reverse("inicio")).status_code, 200)

    def test_registro_rechaza_email_repetido_y_clave_debil(self):
        User.objects.create_user("ana@example.com", "ana@example.com", "x-clave-larga-1")
        r = self.client.post(reverse("registro"), {"nombre": "Ana", "email": "ANA@example.com", "password": "12345678"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ya hay una cuenta con este email")
        self.assertEqual(User.objects.count(), 1)

    def test_entrar_con_email_sin_mayusculas(self):
        User.objects.create_user("ana@example.com", "ana@example.com", "clave-segura-123")
        r = self.client.post(reverse("entrar"), {"username": "ANA@example.com", "password": "clave-segura-123"})
        self.assertRedirects(r, reverse("inicio"))

    def test_entrar_mal(self):
        r = self.client.post(reverse("entrar"), {"username": "nadie@example.com", "password": "x"})
        self.assertContains(r, "no son correctos")

    def test_recuperar_envia_email(self):
        User.objects.create_user("ana@example.com", "ana@example.com", "clave-segura-123")
        r = self.client.post(reverse("recuperar"), {"email": "ana@example.com"})
        self.assertRedirects(r, reverse("recuperar_enviado"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/cuentas/recuperar/", mail.outbox[0].body)

    def test_salir(self):
        u = User.objects.create_user("ana@example.com", "ana@example.com", "clave-segura-123")
        self.client.force_login(u)
        self.assertRedirects(self.client.post(reverse("salir")), reverse("entrar"))
