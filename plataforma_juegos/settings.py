"""
Configuración de Plataforma de Juegos (Sudoku).

Todo lo que cambia entre local y producción se lee de variables de entorno:
DJANGO_SECRET_KEY, DJANGO_DEBUG, DATABASE_URL, EMAIL_HOST_USER/PASSWORD...
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel define VERCEL=1 tanto en el build como en ejecución
ON_VERCEL = bool(os.environ.get("VERCEL"))

# --- Seguridad / entorno ---

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if ON_VERCEL:
        raise RuntimeError("Falta la variable de entorno DJANGO_SECRET_KEY")
    SECRET_KEY = "django-insecure-solo-para-desarrollo-local"

DEBUG = os.environ.get("DJANGO_DEBUG") == "1"

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".vercel.app",
    *filter(None, os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")),
]
CSRF_TRUSTED_ORIGINS = [*filter(None, os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(","))]

if ON_VERCEL:
    # Vercel termina el HTTPS y reenvía la petición a la función
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cuentas.apps.CuentasConfig",
    "sudoku.apps.SudokuConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "plataforma_juegos.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "plataforma_juegos.wsgi.application"

# --- Base de datos ---
# Con DATABASE_URL (Postgres de Supabase) se usa esa base; sin ella, SQLite local.
# conn_max_age=0: en Vercel cada petición cierra su conexión, porque el pooler
# de Supabase en modo sesión solo admite unos pocos clientes a la vez.

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=0,
        ssl_require=bool(os.environ.get("DATABASE_URL")),
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Se entra con el email (ver cuentas/backends.py)
AUTHENTICATION_BACKENDS = ["cuentas.backends.EmailBackend"]
LOGIN_URL = "entrar"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "entrar"

LANGUAGE_CODE = "es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos ---
# Los estilos compilados se versionan en static/; Vercel ejecuta collectstatic
# (porque STATIC_ROOT está definido) y los sirve desde su CDN.

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "static_root"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Email (recuperar contraseña) ---
# Con EMAIL_HOST_USER y EMAIL_HOST_PASSWORD se envía por SMTP (por defecto Gmail,
# con una contraseña de aplicación); sin ellas, los correos salen en la consola.

EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
# Sin espacios ni saltos de línea: Google muestra la contraseña de aplicación en grupos de 4
EMAIL_HOST_PASSWORD = "".join(os.environ.get("EMAIL_HOST_PASSWORD", "").split())
EMAIL_HOST_USER = EMAIL_HOST_USER.strip()

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = True
    EMAIL_TIMEOUT = 10
    DEFAULT_FROM_EMAIL = f"Sudoku <{EMAIL_HOST_USER}>"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "no-reply@sudoku.local"

PASSWORD_RESET_TIMEOUT = 60 * 60  # el enlace caduca en 1 hora

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
