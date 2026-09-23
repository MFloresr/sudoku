# Sudoku

Juego de sudoku web con cuentas de usuario, partidas guardadas y estadísticas.
Hecho con Django, plantillas con Tailwind CSS + daisyUI y Alpine.js.

## Funcionalidades

- **Jugar**:
  - Tablero con resaltado de fila, columna, caja y números iguales.
  - Teclado numérico en pantalla (móvil) y teclado físico: números, flechas, `N` para notas, `Supr` para borrar y `Ctrl+Z` para deshacer.
  - Notas a lápiz, deshacer, borrar y pistas.
  - Cronómetro con pausa y 3 vidas.
- **El servidor valida cada jugada.** La solución nunca llega al navegador, así que no se puede hacer trampa mirando el código de la página.
- **Partidas por usuario.** El progreso, las notas, los errores y el tiempo se guardan en cada jugada; "Continuar" retoma la partida y "Reintentar" empieza de cero tras perder.
- **Victoria y derrota.** Pantalla final con tiempo, errores, pistas y aviso de récord.
- **Sudokus**:
  - Listado por estado (nuevos, en curso, resueltos) y por dificultad, con miniaturas.
  - "Nueva partida" elige al azar uno que no hayas jugado.
- **Perfil**: resueltos, racha de días, porcentaje sin perder, y récord y media por dificultad.
- **Cuentas**: registro, entrada con email y recuperación de contraseña por email.
- **Motor propio** (`sudoku/motor.py`):
  - Resolvedor por vuelta atrás, que comprueba que la solución es única.
  - Calificador que resuelve como una persona (singles, candidatos bloqueados, parejas) para asignar la dificultad.
  - Generador de sudokus nuevos por dificultad.
- **Admin**: alta de sudokus validada (solución única y dificultad calculada) y consulta de partidas.

## Estructura

```text
plataforma_juegos/   configuración de Django (settings por variables de entorno)
sudoku/              juego: modelos Sudoku y Partida, motor, vistas, API JSON, estadísticas
  motor.py           resolver, calificar y generar sudokus
  management/        comando generar_sudokus
cuentas/             registro, entrar (con email), recuperar contraseña
templates/base.html  plantilla común (barra superior en escritorio, inferior en móvil)
estilos/app.css      fuente de los estilos (tema "papel" de daisyUI)
static/              estilos compilados, Alpine.js y static/js/juego.js (lógica del tablero)
```

## Puesta en marcha (local)

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py generar_sudokus --facil 60 --media 60 --dificil 60 --semilla 2026
python manage.py createsuperuser
set DJANGO_DEBUG=1                 # PowerShell: $env:DJANGO_DEBUG = "1"
python manage.py runserver
```

Sin `DATABASE_URL` se usa SQLite (`db.sqlite3`). Los correos de recuperación se
muestran en la consola si no hay configuración de email.

### Estilos

Los estilos compilados (`static/css/app.css`) y Alpine.js (`static/js/alpine.min.js`)
se versionan en el repositorio, así que solo hace falta Node para cambiarlos:

```bash
npm install
npm run build      # o "npm run dev" para recompilar al guardar
```

### Pruebas

```bash
python manage.py test
```

## API de la partida

Todas son `POST` con JSON, requieren sesión y devuelven `{"partida": {...}}` con el
estado actualizado. Cada petición puede incluir `segundos`, el tiempo de juego que lleva el navegador.

| Ruta | Cuerpo | Qué hace |
|---|---|---|
| `/partidas/<id>/jugada/` | `{"celda": 0-80, "numero": 1-9}` | Coloca un número; si es incorrecto suma un error |
| `/partidas/<id>/borrar/` | `{"celda": n}` | Quita el número o las notas de la casilla |
| `/partidas/<id>/notas/` | `{"celda": n, "notas": [1, 5]}` | Guarda las notas de la casilla |
| `/partidas/<id>/pista/` | `{"celda": n}` | Rellena la casilla con su valor |
| `/partidas/<id>/tiempo/` | `{"segundos": n}` | Guarda el tiempo |

## Variables de entorno (producción)

| Variable | Descripción |
|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta (obligatoria en Vercel). |
| `DATABASE_URL` | Conexión a PostgreSQL. |
| `DJANGO_ALLOWED_HOSTS` | Opcional: dominios propios separados por comas. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Opcional: orígenes con https para dominios propios. |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Cuenta de Gmail y contraseña de aplicación para los correos. |

## Autor

Mario Flores Rodríguez
