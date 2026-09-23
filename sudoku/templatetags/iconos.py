from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# Iconos de trazo 24x24 (heredan el color del texto)
TRAZOS = {
    "inicio": '<path d="M4 11l8-7 8 7v9a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z"/>',
    "cuadricula": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M9 3v18M15 3v18M3 9h18M3 15h18"/>',
    "usuario": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
    "atras": '<path d="M15 5l-7 7 7 7"/>',
    "adelante": '<path d="M9 5l7 7-7 7"/>',
    "reloj": '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2M10 2h4"/>',
    "deshacer": '<path d="M9 14L4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
    "borrar": '<path d="M20 5H9l-6 7 6 7h11a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1z"/><path d="M13 10l4 4M17 10l-4 4"/>',
    "lapiz": '<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/>',
    "bombilla": '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    "pausa": '<path d="M9 5v14M15 5v14"/>',
    "play": '<path d="M7 4.5v15l12-7.5z"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7"/>',
    "cruz": '<path d="M6 6l12 12M18 6L6 18"/>',
    "salir": '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l-5-5 5-5M5 12h11"/>',
    "corazon": '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    "trofeo": '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/>',
}


@register.simple_tag
def icono(nombre, tam=22, grosor=1.8, clase=""):
    return format_html(
        '<svg width="{}" height="{}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{}" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="shrink-0 {}">{}</svg>',
        tam, tam, grosor, clase, mark_safe(TRAZOS[nombre]),
    )


@register.inclusion_tag("sudoku/_logo.html")
def logo(grande=False):
    return {"grande": grande}


@register.filter
def tiempo(segundos):
    """512 -> '08:32'."""
    from sudoku.estadisticas import formato_tiempo

    return formato_tiempo(segundos)
