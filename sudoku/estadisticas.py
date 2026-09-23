"""Estadísticas de un jugador a partir de sus partidas terminadas."""

from datetime import timedelta

from django.db.models import Avg, Count, Min
from django.utils import timezone

from .models import Partida, Sudoku


def formato_tiempo(segundos):
    """3725 -> '1:02:05'; 512 -> '08:32'."""
    if segundos is None:
        return "—"
    segundos = int(segundos)
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def racha(usuario, hoy=None):
    """Días seguidos (hasta hoy o ayer) en los que se ha resuelto al menos un sudoku."""
    hoy = hoy or timezone.localdate()
    dias = {
        timezone.localtime(t).date()
        for t in Partida.objects.filter(usuario=usuario, estado=Partida.GANADA).values_list("terminada", flat=True)
        if t
    }
    dia = hoy if hoy in dias else hoy - timedelta(days=1)
    cuenta = 0
    while dia in dias:
        cuenta += 1
        dia -= timedelta(days=1)
    return cuenta


def resumen(usuario):
    partidas = Partida.objects.filter(usuario=usuario)
    ganadas = partidas.filter(estado=Partida.GANADA)
    n_ganadas = ganadas.count()
    n_perdidas = partidas.filter(estado=Partida.PERDIDA).count()

    por_nivel = {
        fila["sudoku__dificultad"]: fila
        for fila in ganadas.values("sudoku__dificultad").annotate(
            hechos=Count("id"), record=Min("segundos"), media=Avg("segundos")
        )
    }
    niveles = []
    for clave, nombre in Sudoku.DIFICULTADES:
        fila = por_nivel.get(clave, {})
        niveles.append(
            {
                "clave": clave,
                "nombre": nombre,
                "hechos": fila.get("hechos", 0),
                "record": formato_tiempo(fila.get("record")),
                "media": formato_tiempo(fila.get("media")),
            }
        )

    terminadas = n_ganadas + n_perdidas
    return {
        "resueltos": n_ganadas,
        "racha": racha(usuario),
        "exito": round(n_ganadas * 100 / terminadas) if terminadas else None,
        "niveles": niveles,
        "record_facil": niveles[0]["record"],
    }
