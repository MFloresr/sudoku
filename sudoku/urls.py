from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("nueva/", views.nueva_partida, name="nueva_partida"),
    path("sudokus/", views.lista, name="lista"),
    path("sudokus/<int:sudoku_id>/", views.jugar, name="jugar"),
    path("sudokus/<int:sudoku_id>/reintentar/", views.reintentar, name="reintentar"),
    path("partidas/<int:partida_id>/", views.ver_partida, name="ver_partida"),
    path("perfil/", views.perfil, name="perfil"),
    # API de la partida (JSON)
    path("partidas/<int:partida_id>/jugada/", views.api_jugada, name="api_jugada"),
    path("partidas/<int:partida_id>/borrar/", views.api_borrar, name="api_borrar"),
    path("partidas/<int:partida_id>/notas/", views.api_notas, name="api_notas"),
    path("partidas/<int:partida_id>/pista/", views.api_pista, name="api_pista"),
    path("partidas/<int:partida_id>/tiempo/", views.api_tiempo, name="api_tiempo"),
]
