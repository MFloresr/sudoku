import json
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import estadisticas, motor
from .forms import SudokuAdminForm
from .models import Partida, Sudoku

PUZZLE = "000260701680070090190004500820100040004602900050003028009300074040050036703018000"
SOLUCION = "435269781682571493197834562826195347374682915951743628519326874248957136763418259"


class MotorTests(TestCase):
    def test_resolver_y_solucion_unica(self):
        celdas = motor.desde_texto(PUZZLE)
        self.assertEqual(motor.a_texto(motor.solucion_unica(celdas)), SOLUCION)

    def test_acepta_json_9x9(self):
        matriz = json.dumps(motor.a_matriz(motor.desde_texto(PUZZLE)))
        self.assertEqual(motor.a_texto(motor.desde_texto(matriz)), PUZZLE)

    def test_detecta_tableros_malos(self):
        with self.assertRaises(motor.TableroInvalido):
            motor.desde_texto("123")
        repetido = "11" + PUZZLE[2:]
        with self.assertRaises(motor.TableroInvalido):
            motor.solucion_unica(motor.desde_texto(repetido))
        with self.assertRaises(motor.TableroInvalido):  # casi vacío: muchas soluciones
            motor.solucion_unica([0] * 80 + [1])

    def test_generar_cada_dificultad(self):
        azar = random.Random(7)
        for dificultad in ("facil", "media", "dificil"):
            puzzle, solucion = motor.generar(dificultad, azar)
            self.assertEqual(motor.resolver(puzzle, limite=2)[0], 1)
            self.assertEqual(motor.calificar(puzzle), dificultad)
            self.assertTrue(all(p in (0, s) for p, s in zip(puzzle, solucion)))

    def test_comando_generar(self):
        call_command("generar_sudokus", facil=2, dificil=1, semilla=3, stdout=open("nul" if __import__("os").name == "nt" else "/dev/null", "w"))
        self.assertEqual(Sudoku.objects.filter(origen="generado").count(), 3)


class BaseJuego(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ana@example.com", "ana@example.com", "clave-segura-123", first_name="Ana")
        self.sudoku = Sudoku.objects.create(puzzle=PUZZLE, solucion=SOLUCION, huecos=PUZZLE.count("0"), dificultad="media")
        self.client.force_login(self.user)

    def partida(self):
        return Partida.objects.create(usuario=self.user, sudoku=self.sudoku, tablero=PUZZLE)


class PartidaTests(BaseJuego):
    def test_jugada_correcta_e_incorrecta(self):
        p = self.partida()
        self.assertTrue(p.jugar(0, 4))
        self.assertEqual(p.tablero[0], "4")
        self.assertFalse(p.jugar(1, 9))
        self.assertEqual(p.errores, 1)
        self.assertIsNone(p.jugar(3, 5))  # casilla del enunciado

    def test_colocar_quita_la_nota_en_los_vecinos(self):
        p = self.partida()
        p.poner_notas(1, [3, 4, 5])
        p.jugar(0, 4)
        self.assertEqual(p.notas["1"], [3, 5])

    def test_tres_errores_pierde(self):
        p = self.partida()
        for _ in range(3):
            p.jugar(0, 9)
        self.assertEqual(p.estado, Partida.PERDIDA)
        self.assertIsNone(p.jugar(0, 4))

    def test_completar_gana(self):
        p = self.partida()
        for i, (a, b) in enumerate(zip(PUZZLE, SOLUCION)):
            if a == "0":
                p.jugar(i, int(b))
        self.assertEqual(p.estado, Partida.GANADA)
        self.assertEqual(p.progreso, 100)
        self.assertIsNotNone(p.terminada)

    def test_pista_y_borrar(self):
        p = self.partida()
        celda, valor = p.pista(0)
        self.assertEqual((celda, valor), (0, 4))
        self.assertEqual(p.pistas, 1)
        self.assertTrue(p.borrar(0))
        self.assertFalse(p.borrar(3))  # del enunciado

    def test_el_tiempo_no_avanza_mas_rapido_que_el_reloj(self):
        p = self.partida()
        p.registrar_tiempo(100000)
        self.assertLess(p.segundos, 60)


class VistasTests(BaseJuego):
    def post_json(self, nombre, partida, datos):
        return self.client.post(reverse(nombre, args=[partida.pk]), json.dumps(datos), content_type="application/json")

    def test_hace_falta_iniciar_sesion(self):
        self.client.logout()
        self.assertRedirects(self.client.get(reverse("inicio")), reverse("entrar") + "?next=/")

    def test_jugar_crea_una_sola_partida_y_la_api_juega(self):
        self.client.get(reverse("jugar", args=[self.sudoku.pk]))
        self.client.get(reverse("jugar", args=[self.sudoku.pk]))
        p = Partida.objects.get()
        r = self.post_json("api_jugada", p, {"celda": 0, "numero": 4, "segundos": 3}).json()
        self.assertTrue(r["correcto"])
        self.assertEqual(r["partida"]["tablero"][0], "4")
        r = self.post_json("api_jugada", p, {"celda": 1, "numero": 9}).json()
        self.assertFalse(r["correcto"])
        self.assertEqual(r["partida"]["vidas"], 2)
        r = self.post_json("api_notas", p, {"celda": 2, "notas": [5, 1]}).json()
        self.assertEqual(r["partida"]["notas"]["2"], [1, 5])

    def test_la_solucion_no_llega_al_navegador(self):
        html = self.client.get(reverse("jugar", args=[self.sudoku.pk])).content.decode()
        self.assertNotIn(SOLUCION, html)

    def test_no_se_puede_tocar_la_partida_de_otro(self):
        otro = User.objects.create_user("bea@example.com", "bea@example.com", "clave-segura-123")
        p = Partida.objects.create(usuario=otro, sudoku=self.sudoku, tablero=PUZZLE)
        self.assertEqual(self.post_json("api_jugada", p, {"celda": 0, "numero": 4}).status_code, 404)

    def test_reintentar_tras_perder_empieza_de_cero(self):
        p = self.partida()
        p.errores, p.estado = 3, Partida.PERDIDA
        p.save()
        self.client.post(reverse("reintentar", args=[self.sudoku.pk]))
        nueva = Partida.objects.get(estado=Partida.EN_CURSO)
        self.assertNotEqual(nueva.pk, p.pk)
        self.assertEqual(nueva.errores, 0)

    def test_nueva_partida_elige_la_dificultad(self):
        r = self.client.post(reverse("nueva_partida"), {"dificultad": "media"})
        self.assertRedirects(r, reverse("jugar", args=[self.sudoku.pk]), fetch_redirect_response=False)

    def test_paginas_cargan(self):
        self.partida()
        for nombre in ("inicio", "lista", "perfil"):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
        for ver in ("en_curso", "resueltos"):
            self.assertEqual(self.client.get(reverse("lista"), {"ver": ver}).status_code, 200)


class EstadisticasTests(BaseJuego):
    def test_racha_y_resumen(self):
        ahora = timezone.now()
        for dias, segundos in ((0, 300), (1, 200), (3, 100)):
            Partida.objects.create(
                usuario=self.user, sudoku=self.sudoku, tablero=SOLUCION, estado=Partida.GANADA,
                segundos=segundos, terminada=ahora - timedelta(days=dias),
            )
        self.assertEqual(estadisticas.racha(self.user), 2)
        r = estadisticas.resumen(self.user)
        self.assertEqual(r["resueltos"], 3)
        self.assertEqual(r["niveles"][1]["record"], "01:40")
        self.assertEqual(estadisticas.formato_tiempo(3725), "1:02:05")


class AdminFormTests(TestCase):
    def test_calcula_solucion_y_dificultad(self):
        form = SudokuAdminForm(data={"puzzle": PUZZLE, "dificultad": "facil", "origen": "manual", "calcular_dificultad": "on"})
        self.assertTrue(form.is_valid(), form.errors)
        s = form.save()
        self.assertEqual(s.solucion, SOLUCION)
        self.assertEqual(s.huecos, PUZZLE.count("0"))

    def test_rechaza_varias_soluciones(self):
        form = SudokuAdminForm(data={"puzzle": "0" * 81, "dificultad": "facil", "origen": "manual"})
        self.assertFalse(form.is_valid())
