from django.contrib import admin

from .forms import SudokuAdminForm
from .models import Partida, Sudoku


@admin.register(Sudoku)
class SudokuAdmin(admin.ModelAdmin):
    form = SudokuAdminForm
    list_display = ("id", "dificultad", "huecos", "origen", "creado")
    list_filter = ("dificultad", "origen")
    readonly_fields = ("solucion", "huecos", "creado")


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "sudoku", "estado", "errores", "pistas", "segundos", "actualizada")
    list_filter = ("estado", "sudoku__dificultad")
    search_fields = ("usuario__email", "usuario__first_name")
    raw_id_fields = ("sudoku",)
