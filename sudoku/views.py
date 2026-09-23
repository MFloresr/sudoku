import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import estadisticas
from .models import VIDAS, Partida, Sudoku

NIVELES = [
    {"clave": Sudoku.FACIL, "nombre": "Fácil", "detalle": "Muchas pistas · unos 5–10 min", "barras": 1},
    {"clave": Sudoku.MEDIA, "nombre": "Media", "detalle": "Hay que pensar · unos 10–20 min", "barras": 2},
    {"clave": Sudoku.DIFICIL, "nombre": "Difícil", "detalle": "Para expertos · más de 20 min", "barras": 3},
]


def mini_tablero(texto, base=None):
    """Casillas para dibujar un tablero pequeño: valor y si es del enunciado."""
    base = base or texto
    return [{"v": "" if v == "0" else v, "dada": b != "0"} for v, b in zip(texto, base)]


# ---------- Páginas ----------

@login_required
def inicio(request):
    en_curso = (
        Partida.objects.filter(usuario=request.user, estado=Partida.EN_CURSO)
        .select_related("sudoku")
        .first()
    )
    return render(
        request,
        "sudoku/inicio.html",
        {
            "en_curso": en_curso,
            "mini": mini_tablero(en_curso.tablero, en_curso.sudoku.puzzle) if en_curso else None,
            "niveles": NIVELES,
            "stats": estadisticas.resumen(request.user),
        },
    )


@login_required
@require_POST
def nueva_partida(request):
    """Empieza un sudoku al azar de la dificultad elegida, priorizando los no jugados."""
    dificultad = request.POST.get("dificultad")
    if dificultad not in dict(Sudoku.DIFICULTADES):
        return redirect("inicio")
    candidatos = Sudoku.objects.filter(dificultad=dificultad)
    sudoku = candidatos.exclude(partidas__usuario=request.user).order_by("?").first()
    if sudoku is None:
        # Ya los ha jugado todos: uno cualquiera sin partida en curso
        sudoku = candidatos.exclude(partidas__usuario=request.user, partidas__estado=Partida.EN_CURSO).order_by("?").first()
    if sudoku is None:
        return redirect("lista")
    return redirect("jugar", sudoku_id=sudoku.pk)


@login_required
def lista(request):
    pestana = request.GET.get("ver", "nuevos")
    dificultad = request.GET.get("dificultad", "")
    if dificultad not in dict(Sudoku.DIFICULTADES):
        dificultad = ""

    if pestana in ("en_curso", "resueltos"):
        estado = Partida.EN_CURSO if pestana == "en_curso" else Partida.GANADA
        qs = Partida.objects.filter(usuario=request.user, estado=estado).select_related("sudoku")
        if dificultad:
            qs = qs.filter(sudoku__dificultad=dificultad)
        pagina = Paginator(qs, 12).get_page(request.GET.get("pagina"))
        tarjetas = [
            {
                "sudoku": p.sudoku,
                "url": reverse("jugar", args=[p.sudoku_id]) if estado == Partida.EN_CURSO else reverse("ver_partida", args=[p.pk]),
                "mini": mini_tablero(p.tablero, p.sudoku.puzzle),
                "estado": (
                    f"{estadisticas.formato_tiempo(p.segundos)} · {p.vidas} {'vida' if p.vidas == 1 else 'vidas'} · {p.progreso} %"
                    if estado == Partida.EN_CURSO
                    else f"Resuelto en {estadisticas.formato_tiempo(p.segundos)}"
                ),
            }
            for p in pagina
        ]
    else:
        pestana = "nuevos"
        qs = Sudoku.objects.exclude(partidas__usuario=request.user)
        if dificultad:
            qs = qs.filter(dificultad=dificultad)
        pagina = Paginator(qs, 12).get_page(request.GET.get("pagina"))
        tarjetas = [
            {"sudoku": s, "url": reverse("jugar", args=[s.pk]), "mini": mini_tablero(s.puzzle), "estado": f"{s.huecos} casillas por rellenar"}
            for s in pagina
        ]

    return render(
        request,
        "sudoku/lista.html",
        {
            "tarjetas": tarjetas,
            "pagina": pagina,
            "pestana": pestana,
            "dificultad": dificultad,
            "pestanas": [("nuevos", "Nuevos"), ("en_curso", "En curso"), ("resueltos", "Resueltos")],
            "dificultades": Sudoku.DIFICULTADES,
        },
    )


@login_required
def jugar(request, sudoku_id):
    """Abre la partida en curso de este sudoku o crea una nueva."""
    sudoku = get_object_or_404(Sudoku, pk=sudoku_id)
    partida = Partida.objects.filter(usuario=request.user, sudoku=sudoku, estado=Partida.EN_CURSO).first()
    if partida is None:
        try:
            with transaction.atomic():
                partida = Partida.objects.create(usuario=request.user, sudoku=sudoku, tablero=sudoku.puzzle)
        except IntegrityError:  # doble clic: ya la creó la otra petición
            partida = Partida.objects.get(usuario=request.user, sudoku=sudoku, estado=Partida.EN_CURSO)
    return _pantalla_juego(request, partida)


@login_required
def ver_partida(request, partida_id):
    """Una partida concreta (también terminada, para ver el resultado)."""
    partida = get_object_or_404(Partida.objects.select_related("sudoku"), pk=partida_id, usuario=request.user)
    return _pantalla_juego(request, partida)


def _pantalla_juego(request, partida):
    sudoku = partida.sudoku
    record = (
        Partida.objects.filter(usuario=request.user, sudoku__dificultad=sudoku.dificultad, estado=Partida.GANADA)
        .exclude(pk=partida.pk)
        .order_by("segundos")
        .values_list("segundos", flat=True)
        .first()
    )
    datos = {
        "puzzle": sudoku.puzzle,
        "partida": partida.estado_para_cliente(),
        "vidasTotales": VIDAS,
        "recordAnterior": record,
        "urls": {
            "jugada": f"/partidas/{partida.pk}/jugada/",
            "borrar": f"/partidas/{partida.pk}/borrar/",
            "notas": f"/partidas/{partida.pk}/notas/",
            "pista": f"/partidas/{partida.pk}/pista/",
            "tiempo": f"/partidas/{partida.pk}/tiempo/",
        },
    }
    return render(request, "sudoku/jugar.html", {"partida": partida, "sudoku": sudoku, "datos": datos})


@login_required
@require_POST
def reintentar(request, sudoku_id):
    """Empieza de cero un sudoku (si no hay ya una partida en curso)."""
    sudoku = get_object_or_404(Sudoku, pk=sudoku_id)
    try:
        with transaction.atomic():
            Partida.objects.get_or_create(
                usuario=request.user, sudoku=sudoku, estado=Partida.EN_CURSO, defaults={"tablero": sudoku.puzzle}
            )
    except IntegrityError:
        pass
    return redirect("jugar", sudoku_id=sudoku.pk)


@login_required
def perfil(request):
    ultimas = (
        Partida.objects.filter(usuario=request.user)
        .exclude(estado=Partida.EN_CURSO)
        .select_related("sudoku")
        .order_by("-terminada")[:5]
    )
    return render(
        request,
        "sudoku/perfil.html",
        {
            "stats": estadisticas.resumen(request.user),
            "ultimas": [
                {"partida": p, "tiempo": estadisticas.formato_tiempo(p.segundos)} for p in ultimas
            ],
        },
    )


# ---------- API de la partida (JSON) ----------

def _partida_del_usuario(request, partida_id):
    return get_object_or_404(
        Partida.objects.select_related("sudoku").select_for_update(of=("self",)), pk=partida_id, usuario=request.user
    )


def _leer_json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _celda(datos):
    try:
        celda = int(datos.get("celda"))
    except (TypeError, ValueError):
        return None
    return celda if 0 <= celda < 81 else None


def _respuesta(partida, **extra):
    return JsonResponse({"partida": partida.estado_para_cliente(), **extra})


def api(accion):
    """Decorador común: login, POST, JSON válido, bloqueo de la fila y tiempo actualizado."""

    def decorador(vista):
        @login_required
        @require_POST
        def envoltura(request, partida_id):
            datos = _leer_json(request)
            if datos is None:
                return JsonResponse({"error": "JSON no válido"}, status=400)
            with transaction.atomic():
                partida = _partida_del_usuario(request, partida_id)
                if "segundos" in datos:
                    try:
                        partida.registrar_tiempo(int(datos["segundos"]))
                    except (TypeError, ValueError):
                        pass
                respuesta = vista(request, partida, datos)
                partida.save()
            return respuesta

        envoltura.__name__ = f"api_{accion}"
        return envoltura

    return decorador


@api("jugada")
def api_jugada(request, partida, datos):
    celda = _celda(datos)
    try:
        numero = int(datos.get("numero"))
    except (TypeError, ValueError):
        numero = 0
    if celda is None or not 1 <= numero <= 9:
        return JsonResponse({"error": "Casilla o número no válidos"}, status=400)
    correcto = partida.jugar(celda, numero)
    return _respuesta(partida, correcto=correcto)


@api("borrar")
def api_borrar(request, partida, datos):
    celda = _celda(datos)
    if celda is None:
        return JsonResponse({"error": "Casilla no válida"}, status=400)
    partida.borrar(celda)
    return _respuesta(partida)


@api("notas")
def api_notas(request, partida, datos):
    celda = _celda(datos)
    numeros = datos.get("notas")
    if celda is None or not isinstance(numeros, list):
        return JsonResponse({"error": "Datos no válidos"}, status=400)
    try:
        partida.poner_notas(celda, numeros)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Notas no válidas"}, status=400)
    return _respuesta(partida)


@api("pista")
def api_pista(request, partida, datos):
    resultado = partida.pista(_celda(datos))
    if resultado is None:
        return _respuesta(partida, pista=None)
    return _respuesta(partida, pista={"celda": resultado[0], "valor": resultado[1]})


@api("tiempo")
def api_tiempo(request, partida, datos):
    return _respuesta(partida)
