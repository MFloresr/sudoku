from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from . import motor

VIDAS = 3


class Sudoku(models.Model):
    """Un tablero para jugar. Los tableros se guardan como 81 dígitos (0 = vacía)."""

    FACIL, MEDIA, DIFICIL = "facil", "media", "dificil"
    DIFICULTADES = [(FACIL, "Fácil"), (MEDIA, "Media"), (DIFICIL, "Difícil")]

    ORIGENES = [("generado", "Generado"), ("importado", "Importado"), ("manual", "Manual")]

    puzzle = models.CharField(max_length=81, help_text="81 dígitos, 0 = casilla vacía")
    solucion = models.CharField(max_length=81, editable=False)
    dificultad = models.CharField(max_length=10, choices=DIFICULTADES, default=MEDIA, db_index=True)
    huecos = models.PositiveSmallIntegerField(default=0, editable=False)
    origen = models.CharField(max_length=10, choices=ORIGENES, default="manual")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Sudoku #{self.pk} ({self.get_dificultad_display()})"

    @property
    def nombre(self):
        return f"Sudoku #{self.pk}"

    def completar_desde_puzzle(self, calcular_dificultad=True):
        """Valida el puzzle y calcula solución, huecos y dificultad. Lanza motor.TableroInvalido."""
        celdas = motor.desde_texto(self.puzzle)
        self.solucion = motor.a_texto(motor.solucion_unica(celdas))
        self.puzzle = motor.a_texto(celdas)
        self.huecos = celdas.count(0)
        if calcular_dificultad:
            self.dificultad = motor.calificar(celdas)


class Partida(models.Model):
    """Una partida de un usuario a un sudoku. Solo se guardan los números correctos."""

    EN_CURSO, GANADA, PERDIDA = "en_curso", "ganada", "perdida"
    ESTADOS = [(EN_CURSO, "En curso"), (GANADA, "Ganada"), (PERDIDA, "Perdida")]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="partidas")
    sudoku = models.ForeignKey(Sudoku, on_delete=models.CASCADE, related_name="partidas")
    estado = models.CharField(max_length=10, choices=ESTADOS, default=EN_CURSO)
    tablero = models.CharField(max_length=81)
    notas = models.JSONField(default=dict, blank=True, help_text='{"40": [1, 8]}: notas por casilla')
    errores = models.PositiveSmallIntegerField(default=0)
    pistas = models.PositiveSmallIntegerField(default=0)
    segundos = models.PositiveIntegerField(default=0)
    empezada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)
    terminada = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-actualizada"]
        indexes = [models.Index(fields=["usuario", "estado"])]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "sudoku"],
                condition=Q(estado="en_curso"),
                name="una_partida_en_curso_por_sudoku",
            )
        ]

    def __str__(self):
        return f"{self.usuario} · {self.sudoku} · {self.get_estado_display()}"

    # ---------- Datos derivados ----------

    @property
    def vidas(self):
        return max(0, VIDAS - self.errores)

    @property
    def en_curso(self):
        return self.estado == self.EN_CURSO

    @property
    def progreso(self):
        """Porcentaje de huecos ya rellenados."""
        huecos = self.sudoku.huecos or 1
        puestos = sum(1 for a, b in zip(self.tablero, self.sudoku.puzzle) if a != "0" and b == "0")
        return round(puestos * 100 / huecos)

    def estado_para_cliente(self):
        return {
            "id": self.pk,
            "tablero": self.tablero,
            "notas": self.notas,
            "errores": self.errores,
            "vidas": self.vidas,
            "pistas": self.pistas,
            "segundos": self.segundos,
            "estado": self.estado,
        }

    # ---------- Jugadas (las valida el servidor: la solución no sale nunca al navegador) ----------

    def _celda_editable(self, celda):
        return self.en_curso and 0 <= celda < 81 and self.sudoku.puzzle[celda] == "0"

    def _poner(self, celda, valor):
        t = list(self.tablero)
        t[celda] = str(valor)
        self.tablero = "".join(t)
        self.notas.pop(str(celda), None)
        # El número colocado deja de ser candidato en fila, columna y caja
        for j in motor.VECINOS[celda]:
            clave = str(j)
            if clave in self.notas and valor in self.notas[clave]:
                self.notas[clave] = [n for n in self.notas[clave] if n != valor]
                if not self.notas[clave]:
                    del self.notas[clave]

    def _comprobar_fin(self):
        if self.tablero == self.sudoku.solucion:
            self.estado = self.GANADA
            self.terminada = timezone.now()
        elif self.errores >= VIDAS:
            self.estado = self.PERDIDA
            self.terminada = timezone.now()

    def jugar(self, celda, numero):
        """Coloca un número. Devuelve True si es correcto; si no, suma un error."""
        if not self._celda_editable(celda) or not 1 <= numero <= 9:
            return None
        correcto = int(self.sudoku.solucion[celda]) == numero
        if correcto:
            self._poner(celda, numero)
        else:
            self.errores += 1
        self._comprobar_fin()
        return correcto

    def borrar(self, celda):
        """Quita el número colocado (o las notas) de una casilla que no es del enunciado."""
        if not self._celda_editable(celda):
            return False
        t = list(self.tablero)
        t[celda] = "0"
        self.tablero = "".join(t)
        self.notas.pop(str(celda), None)
        return True

    def poner_notas(self, celda, numeros):
        if not self._celda_editable(celda) or self.tablero[celda] != "0":
            return False
        limpios = sorted({int(n) for n in numeros if 1 <= int(n) <= 9})
        if limpios:
            self.notas[str(celda)] = limpios
        else:
            self.notas.pop(str(celda), None)
        return True

    def pista(self, celda=None):
        """Rellena una casilla vacía (la indicada o la primera) con su valor. Devuelve (celda, valor)."""
        if not self.en_curso:
            return None
        if celda is None or not self._celda_editable(celda) or self.tablero[celda] != "0":
            vacias = [i for i, v in enumerate(self.tablero) if v == "0"]
            if not vacias:
                return None
            celda = vacias[0]
        valor = int(self.sudoku.solucion[celda])
        self._poner(celda, valor)
        self.pistas += 1
        self._comprobar_fin()
        return celda, valor

    def registrar_tiempo(self, segundos):
        """Acepta el tiempo del navegador sin permitir que avance más deprisa que el reloj real."""
        if not self.en_curso:
            return
        transcurrido = (timezone.now() - self.actualizada).total_seconds() if self.actualizada else 0
        maximo = self.segundos + int(transcurrido) + 5
        self.segundos = max(self.segundos, min(int(segundos), maximo))
