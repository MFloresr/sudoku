from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Sudoku · Administración"
admin.site.site_title = "Sudoku"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("cuentas.urls")),
    path("", include("sudoku.urls")),
]
