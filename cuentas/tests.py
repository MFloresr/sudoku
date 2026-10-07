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


class DemoTests(TestCase):
    PUZZLE = "000260701680070090190004500820100040004602900050003028009300074040050036703018000"
    SOLUCION = "435269781682571493197834562826195347374682915951743628519326874248957136763418259"

    def setUp(self):
        from sudoku.models import Sudoku

        for nivel, n in (("facil", 8), ("media", 6), ("dificil", 2)):
            for _ in range(n):
                Sudoku.objects.create(
                    puzzle=self.PUZZLE, solucion=self.SOLUCION, huecos=self.PUZZLE.count("0"), dificultad=nivel
                )

    def test_boton_crea_la_cuenta_y_entra(self):
        r = self.client.post(reverse("demo"))
        self.assertRedirects(r, reverse("inicio"))
        u = User.objects.get(email="demo@example.com")
        self.assertFalse(u.is_staff or u.is_superuser)
        self.assertEqual(self.client.get(reverse("inicio")).status_code, 200)

    def test_tiene_partidas_y_estadisticas(self):
        from sudoku import estadisticas
        from sudoku.models import Partida

        self.client.get(reverse("demo"))
        u = User.objects.get(email="demo@example.com")
        self.assertEqual(u.partidas.filter(estado=Partida.GANADA).count(), 10)
        self.assertEqual(u.partidas.filter(estado=Partida.PERDIDA).count(), 1)
        self.assertEqual(u.partidas.filter(estado=Partida.EN_CURSO).count(), 1)
        self.assertGreaterEqual(estadisticas.resumen(u)["racha"], 10)

    def test_se_reinicia_si_lleva_mas_de_una_hora_sin_uso(self):
        from datetime import timedelta

        from django.utils import timezone

        self.client.get(reverse("demo"))
        u = User.objects.get(email="demo@example.com")
        u.partidas.first().delete()
        User.objects.filter(pk=u.pk).update(last_login=timezone.now() - timedelta(hours=2))
        self.client.logout()
        self.client.get(reverse("demo"))
        self.assertEqual(u.partidas.count(), 12)

    def test_no_se_reinicia_si_se_esta_usando(self):
        self.client.get(reverse("demo"))
        u = User.objects.get(email="demo@example.com")
        u.partidas.first().delete()
        self.client.logout()
        self.client.get(reverse("demo"))
        self.assertEqual(u.partidas.count(), 11)

    def test_entrar_a_mano_tambien_la_prepara(self):
        from datetime import timedelta

        from django.conf import settings
        from django.utils import timezone

        self.client.get(reverse("demo"))
        u = User.objects.get(email="demo@example.com")
        u.partidas.all().delete()
        User.objects.filter(pk=u.pk).update(last_login=timezone.now() - timedelta(hours=2))
        self.client.logout()
        r = self.client.post(reverse("entrar"), {"username": settings.DEMO_EMAIL, "password": settings.DEMO_PASSWORD})
        self.assertRedirects(r, reverse("inicio"))
        self.assertEqual(u.partidas.count(), 12)
        # La sesión sigue siendo válida tras regenerar la demo
        self.assertEqual(self.client.get(reverse("inicio")).status_code, 200)

    def test_no_se_puede_recuperar_su_contrasena(self):
        self.client.get(reverse("demo"))
        self.client.logout()
        self.client.post(reverse("recuperar"), {"email": "demo@example.com"})
        self.assertEqual(len(mail.outbox), 0)

    def test_aviso_de_demo_solo_para_la_demo(self):
        self.client.get(reverse("demo"))
        self.assertContains(self.client.get(reverse("inicio")), "Cuenta de demostración")
        self.client.logout()
        u = User.objects.create_user("ana@example.com", "ana@example.com", "clave-segura-123")
        self.client.force_login(u)
        self.assertNotContains(self.client.get(reverse("inicio")), "Cuenta de demostración")
