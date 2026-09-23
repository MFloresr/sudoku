import random

from django.core.management.base import BaseCommand

from sudoku import motor
from sudoku.models import Sudoku


class Command(BaseCommand):
    help = "Genera sudokus nuevos con solución única y la dificultad pedida."

    def add_arguments(self, parser):
        parser.add_argument("--facil", type=int, default=0)
        parser.add_argument("--media", type=int, default=0)
        parser.add_argument("--dificil", type=int, default=0)
        parser.add_argument("--semilla", type=int, default=None, help="Para generar siempre los mismos")

    def handle(self, *args, **opciones):
        azar = random.Random(opciones["semilla"])
        existentes = set(Sudoku.objects.values_list("puzzle", flat=True))
        for dificultad in (Sudoku.FACIL, Sudoku.MEDIA, Sudoku.DIFICIL):
            creados = 0
            while creados < opciones[dificultad]:
                puzzle, solucion = motor.generar(dificultad, azar)
                texto = motor.a_texto(puzzle)
                if texto in existentes:
                    continue
                existentes.add(texto)
                Sudoku.objects.create(
                    puzzle=texto,
                    solucion=motor.a_texto(solucion),
                    huecos=puzzle.count(0),
                    dificultad=dificultad,
                    origen="generado",
                )
                creados += 1
            if creados:
                self.stdout.write(f"{dificultad}: {creados} sudokus nuevos")
