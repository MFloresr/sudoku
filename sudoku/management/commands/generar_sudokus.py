import random

from django.core.management import color
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from sudoku import motor
from sudoku.models import Partida, Sudoku


class Command(BaseCommand):
    help = "Genera sudokus nuevos con solución única y la dificultad pedida."

    def add_arguments(self, parser):
        parser.add_argument("--facil", type=int, default=0)
        parser.add_argument("--media", type=int, default=0)
        parser.add_argument("--dificil", type=int, default=0)
        parser.add_argument("--semilla", type=int, default=None, help="Para generar siempre los mismos")
        parser.add_argument(
            "--reemplazar-todo",
            action="store_true",
            help="Borra TODOS los sudokus (y sus partidas) y reinicia la numeración antes de generar.",
        )
        parser.add_argument("--si", action="store_true", help="No pedir confirmación con --reemplazar-todo")

    def handle(self, *args, **opciones):
        azar = random.Random(opciones["semilla"])

        # Primero se generan en memoria: si algo falla, la base de datos no se toca
        nuevos = []
        existentes = set() if opciones["reemplazar_todo"] else set(Sudoku.objects.values_list("puzzle", flat=True))
        for dificultad in (Sudoku.FACIL, Sudoku.MEDIA, Sudoku.DIFICIL):
            creados = 0
            while creados < opciones[dificultad]:
                puzzle, solucion = motor.generar(dificultad, azar)
                texto = motor.a_texto(puzzle)
                if texto in existentes:
                    continue
                existentes.add(texto)
                nuevos.append(
                    Sudoku(
                        puzzle=texto,
                        solucion=motor.a_texto(solucion),
                        huecos=puzzle.count(0),
                        dificultad=dificultad,
                        origen="generado",
                    )
                )
                creados += 1

        with transaction.atomic():
            if opciones["reemplazar_todo"]:
                n_sudokus, n_partidas = Sudoku.objects.count(), Partida.objects.count()
                if not opciones["si"]:
                    respuesta = input(
                        f"Se borrarán {n_sudokus} sudokus y {n_partidas} partidas. Escribe 'borrar' para seguir: "
                    )
                    if respuesta.strip() != "borrar":
                        raise CommandError("Cancelado: no se ha tocado nada.")
                Partida.objects.all().delete()
                Sudoku.objects.all().delete()
                # Reinicia la numeración para que los nuevos empiecen en #1
                with connection.cursor() as cursor:
                    for sql in connection.ops.sequence_reset_by_name_sql(
                        color.no_style(), [{"table": Sudoku._meta.db_table, "column": "id"}]
                    ):
                        cursor.execute(sql)
                self.stdout.write(f"Borrados {n_sudokus} sudokus y {n_partidas} partidas.")
            Sudoku.objects.bulk_create(nuevos)

        for dificultad in (Sudoku.FACIL, Sudoku.MEDIA, Sudoku.DIFICIL):
            if opciones[dificultad]:
                self.stdout.write(f"{dificultad}: {opciones[dificultad]} sudokus nuevos")
