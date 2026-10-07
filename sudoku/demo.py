"""
Cuenta de demostración pública.

Cualquiera puede entrar con ella (botón "Probar la demo" o /cuentas/demo/), así que sus
partidas son ficticias y se regeneran solas: al entrar, si nadie la ha usado en la última
hora, se borran sus partidas y se crean de nuevo en torno a la fecha de hoy.
"""
import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Partida, Sudoku

REINICIAR_TRAS = timedelta(hours=1)

# (dificultad, número de partidas ganadas, rango de segundos)
GANADAS = [
    (Sudoku.FACIL, 6, (300, 720)),
    (Sudoku.MEDIA, 3, (780, 1260)),
    (Sudoku.DIFICIL, 1, (1500, 1800)),
]


def es_demo(user):
    return bool(user and user.is_authenticated and user.email.lower() == settings.DEMO_EMAIL.lower())


def debe_reiniciarse(user):
    """Nadie la ha usado en la última hora (last_login antes de hacer login)."""
    return user.last_login is None or timezone.now() - user.last_login > REINICIAR_TRAS


def _rellenar(sudoku, fraccion, azar):
    """Tablero del enunciado con una parte de los huecos ya resueltos (números correctos)."""
    huecos = [i for i, v in enumerate(sudoku.puzzle) if v == "0"]
    puestos = set(azar.sample(huecos, int(len(huecos) * fraccion)))
    return "".join(sudoku.solucion[i] if i in puestos else v for i, v in enumerate(sudoku.puzzle))


@transaction.atomic
def preparar_demo():
    """Crea la cuenta demo si no existe y regenera sus partidas. Devuelve el usuario."""
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="demo", defaults={"email": settings.DEMO_EMAIL, "first_name": "Demo"}
    )
    user.email = settings.DEMO_EMAIL
    user.first_name = "Demo"
    user.is_staff = user.is_superuser = False
    user.set_password(settings.DEMO_PASSWORD)
    user.save()

    Partida.objects.filter(usuario=user).delete()

    # Las mismas partidas durante todo el día, distintas de un día a otro
    ahora = timezone.now()
    azar = random.Random(timezone.localdate().toordinal())
    usados = set()
    partidas, inicios = [], []

    def elegir(dificultad):
        ids = list(Sudoku.objects.filter(dificultad=dificultad).exclude(pk__in=usados).values_list("pk", flat=True))
        if not ids:
            return None
        pk = azar.choice(ids)
        usados.add(pk)
        return Sudoku.objects.get(pk=pk)

    # Ganadas: una por día hacia atrás, así la racha se ve
    dia = 1
    for dificultad, cuantas, (minimo, maximo) in GANADAS:
        for _ in range(cuantas):
            sudoku = elegir(dificultad)
            if sudoku is None:
                continue
            fin = ahora - timedelta(days=dia, hours=azar.randint(0, 5))
            segundos = azar.randint(minimo, maximo)
            partidas.append(Partida(
                usuario=user, sudoku=sudoku, estado=Partida.GANADA, tablero=sudoku.solucion,
                errores=azar.choice([0, 0, 1, 2]), pistas=azar.choice([0, 0, 1]), segundos=segundos, terminada=fin,
            ))
            inicios.append(fin - timedelta(seconds=segundos))
            dia += 1

    sudoku = elegir(Sudoku.MEDIA)
    if sudoku:
        fin = ahora - timedelta(days=dia, hours=2)
        partidas.append(Partida(
            usuario=user, sudoku=sudoku, estado=Partida.PERDIDA, tablero=_rellenar(sudoku, 0.3, azar),
            errores=3, segundos=azar.randint(300, 600), terminada=fin,
        ))
        inicios.append(fin - timedelta(minutes=8))

    sudoku = elegir(Sudoku.MEDIA)
    if sudoku:
        partidas.append(Partida(
            usuario=user, sudoku=sudoku, estado=Partida.EN_CURSO, tablero=_rellenar(sudoku, 0.55, azar),
            errores=1, segundos=azar.randint(360, 540),
        ))
        inicios.append(ahora - timedelta(minutes=10))

    # Pocas consultas: la base de datos está lejos de las funciones de Vercel
    Partida.objects.bulk_create(partidas)
    # empezada y actualizada se rellenan solas al crear; se corrigen para que las fechas cuadren
    for p, f in zip(partidas, inicios):
        p.empezada = f
        p.actualizada = p.terminada or ahora
    Partida.objects.bulk_update(partidas, ["empezada", "actualizada"])
    return user
