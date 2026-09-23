"""
Motor del sudoku: validar, resolver, calificar la dificultad y generar tableros.

Un tablero es una lista de 81 enteros (0 = casilla vacía), fila a fila.
En la base de datos se guarda como texto de 81 dígitos ("530070000...").
"""

import json
import random

TODOS = 0b1111111110  # bits 1..9 = candidatos posibles


def _caja(i):
    fila, col = divmod(i, 9)
    return (fila // 3) * 3 + col // 3


CAJA = [_caja(i) for i in range(81)]
FILAS = [[f * 9 + c for c in range(9)] for f in range(9)]
COLUMNAS = [[f * 9 + c for f in range(9)] for c in range(9)]
CAJAS = [[i for i in range(81) if CAJA[i] == b] for b in range(9)]
UNIDADES = FILAS + COLUMNAS + CAJAS
VECINOS = [
    sorted({j for u in UNIDADES if i in u for j in u} - {i})
    for i in range(81)
]


class TableroInvalido(ValueError):
    """El texto no describe un tablero de sudoku válido."""


# ---------- Conversión ----------

def desde_texto(texto):
    """Acepta 81 dígitos (0 o . = vacía) o una lista JSON de 9 listas de 9 números."""
    texto = (texto or "").strip()
    if texto.startswith("["):
        try:
            matriz = json.loads(texto)
        except json.JSONDecodeError:
            raise TableroInvalido("El tablero no es un JSON válido.")
        if not (isinstance(matriz, list) and len(matriz) == 9 and all(isinstance(f, list) and len(f) == 9 for f in matriz)):
            raise TableroInvalido("El tablero tiene que ser de 9 filas por 9 columnas.")
        celdas = [v for fila in matriz for v in fila]
    else:
        limpio = "".join(ch for ch in texto if not ch.isspace()).replace(".", "0")
        if len(limpio) != 81:
            raise TableroInvalido("El tablero tiene que tener 81 casillas.")
        celdas = list(limpio)
    try:
        celdas = [int(v) for v in celdas]
    except (TypeError, ValueError):
        raise TableroInvalido("Solo se admiten números del 0 al 9.")
    if any(not 0 <= v <= 9 for v in celdas):
        raise TableroInvalido("Solo se admiten números del 0 al 9.")
    return celdas


def a_texto(celdas):
    return "".join(str(v) for v in celdas)


def a_matriz(celdas):
    return [list(celdas[f * 9:(f + 1) * 9]) for f in range(9)]


# ---------- Resolver ----------

def es_consistente(celdas):
    """True si ningún número se repite en una fila, columna o caja."""
    for unidad in UNIDADES:
        vistos = [celdas[i] for i in unidad if celdas[i]]
        if len(vistos) != len(set(vistos)):
            return False
    return True


def resolver(celdas, limite=2, azar=None):
    """
    Busca soluciones por vuelta atrás (eligiendo la casilla con menos opciones).
    Devuelve (número de soluciones hasta `limite`, primera solución o None).
    Con `azar` (random.Random) prueba los números en orden aleatorio.
    """
    tablero = list(celdas)
    filas, cols, cajas = [0] * 9, [0] * 9, [0] * 9
    for i, v in enumerate(tablero):
        if v:
            bit = 1 << v
            f, c, b = i // 9, i % 9, CAJA[i]
            if filas[f] & bit or cols[c] & bit or cajas[b] & bit:
                return 0, None
            filas[f] |= bit
            cols[c] |= bit
            cajas[b] |= bit

    vacias = [i for i, v in enumerate(tablero) if not v]
    encontradas = []
    cuenta = 0

    def buscar():
        nonlocal cuenta
        mejor, mejor_mascara, mejor_n = -1, 0, 10
        for i in vacias:
            if tablero[i]:
                continue
            mascara = TODOS & ~(filas[i // 9] | cols[i % 9] | cajas[CAJA[i]])
            n = bin(mascara).count("1")
            if n < mejor_n:
                mejor, mejor_mascara, mejor_n = i, mascara, n
                if n <= 1:
                    break
        if mejor == -1:
            cuenta += 1
            if not encontradas:
                encontradas.append(list(tablero))
            return
        if mejor_n == 0:
            return
        numeros = [v for v in range(1, 10) if mejor_mascara & (1 << v)]
        if azar:
            azar.shuffle(numeros)
        f, c, b = mejor // 9, mejor % 9, CAJA[mejor]
        for v in numeros:
            bit = 1 << v
            tablero[mejor] = v
            filas[f] |= bit
            cols[c] |= bit
            cajas[b] |= bit
            buscar()
            tablero[mejor] = 0
            filas[f] ^= bit
            cols[c] ^= bit
            cajas[b] ^= bit
            if cuenta >= limite:
                return

    buscar()
    return cuenta, (encontradas[0] if encontradas else None)


def solucion_unica(celdas):
    """Devuelve la solución si el tablero tiene exactamente una; si no, lanza TableroInvalido."""
    if not es_consistente(celdas):
        raise TableroInvalido("Hay números repetidos en una fila, columna o caja.")
    n, solucion = resolver(celdas, limite=2)
    if n == 0:
        raise TableroInvalido("Este sudoku no tiene solución.")
    if n > 1:
        raise TableroInvalido("Este sudoku tiene más de una solución.")
    return solucion


# ---------- Calificar dificultad ----------

def _tecnicas_necesarias(celdas):
    """
    Resuelve como lo haría una persona y devuelve el nivel de técnica más alto usado:
    1 = solo casillas y números únicos (singles), 2 = candidatos bloqueados o parejas,
    3 = no se resuelve con estas técnicas (hace falta tanteo o técnicas avanzadas).
    """
    tablero = list(celdas)
    cand = [0] * 81
    for i in range(81):
        if not tablero[i]:
            usados = 0
            for j in VECINOS[i]:
                usados |= 1 << tablero[j]
            cand[i] = TODOS & ~usados

    def colocar(i, v):
        tablero[i] = v
        cand[i] = 0
        bit = ~(1 << v)
        for j in VECINOS[i]:
            cand[j] &= bit

    nivel = 0
    while True:
        # Casilla con un solo candidato (naked single)
        colocado = False
        for i in range(81):
            if not tablero[i] and cand[i] and cand[i] & (cand[i] - 1) == 0:
                colocar(i, cand[i].bit_length() - 1)
                colocado = True
        # Número que solo cabe en una casilla de la unidad (hidden single)
        for unidad in UNIDADES:
            for v in range(1, 10):
                bit = 1 << v
                sitios = [i for i in unidad if cand[i] & bit]
                if len(sitios) == 1 and not tablero[sitios[0]]:
                    colocar(sitios[0], v)
                    colocado = True
        if colocado:
            nivel = max(nivel, 1)
            continue
        if all(tablero):
            break

        eliminado = False
        # Candidatos bloqueados: dentro de una caja, un número solo en una fila/columna
        for b, caja in enumerate(CAJAS):
            for v in range(1, 10):
                bit = 1 << v
                sitios = [i for i in caja if cand[i] & bit]
                if len(sitios) < 2:
                    continue
                for grupo, clave in ((FILAS, lambda i: i // 9), (COLUMNAS, lambda i: i % 9)):
                    if len({clave(i) for i in sitios}) == 1:
                        for j in grupo[clave(sitios[0])]:
                            if CAJA[j] != b and cand[j] & bit:
                                cand[j] &= ~bit
                                eliminado = True
        # Y al revés: en una fila/columna, un número solo dentro de una caja
        for unidad in FILAS + COLUMNAS:
            for v in range(1, 10):
                bit = 1 << v
                sitios = [i for i in unidad if cand[i] & bit]
                if len(sitios) >= 2 and len({CAJA[i] for i in sitios}) == 1:
                    for j in CAJAS[CAJA[sitios[0]]]:
                        if j not in unidad and cand[j] & bit:
                            cand[j] &= ~bit
                            eliminado = True
        # Parejas desnudas: dos casillas de una unidad con los mismos dos candidatos
        for unidad in UNIDADES:
            parejas = {}
            for i in unidad:
                if bin(cand[i]).count("1") == 2:
                    parejas.setdefault(cand[i], []).append(i)
            for mascara, sitios in parejas.items():
                if len(sitios) == 2:
                    for j in unidad:
                        if j not in sitios and cand[j] & mascara:
                            cand[j] &= ~mascara
                            eliminado = True
        if eliminado:
            nivel = 2
            continue
        break

    return nivel if all(tablero) else 3


def calificar(celdas):
    """Devuelve 'facil', 'media' o 'dificil' según las técnicas necesarias y los huecos."""
    nivel = _tecnicas_necesarias(celdas)
    huecos = celdas.count(0)
    if nivel >= 3:
        return "dificil"
    if nivel == 2 or huecos >= 46:
        return "media"
    return "facil"


# ---------- Generar ----------

# Huecos buscados por dificultad (para que la partida tenga una duración razonable)
HUECOS = {"facil": (38, 44), "media": (46, 52), "dificil": (52, 64)}


def tablero_completo(azar):
    """Un tablero resuelto al azar."""
    _, solucion = resolver([0] * 81, limite=1, azar=azar)
    return solucion


def generar(dificultad, azar=None, intentos=200):
    """
    Genera (puzzle, solucion) con solución única y de la dificultad pedida.
    Quita casillas por parejas simétricas mientras la solución siga siendo única.
    """
    if dificultad not in HUECOS:
        raise ValueError(f"Dificultad desconocida: {dificultad}")
    azar = azar or random.Random()
    minimo, maximo = HUECOS[dificultad]
    for _ in range(intentos):
        solucion = tablero_completo(azar)
        puzzle = list(solucion)
        orden = list(range(41))  # casillas 0..40 y su simétrica 80-i
        azar.shuffle(orden)
        objetivo = azar.randint(minimo, maximo)
        for i in orden:
            if puzzle.count(0) >= objetivo:
                break
            j = 80 - i
            guardados = puzzle[i], puzzle[j]
            puzzle[i] = puzzle[j] = 0
            if resolver(puzzle, limite=2)[0] != 1:
                puzzle[i], puzzle[j] = guardados
        if minimo <= puzzle.count(0) and calificar(puzzle) == dificultad:
            return puzzle, solucion
    raise RuntimeError(f"No se pudo generar un sudoku {dificultad} tras {intentos} intentos")
