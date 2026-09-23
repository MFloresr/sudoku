from django.db import migrations, models


class Migration(migrations.Migration):
    """Paso 1 de 3: añade los campos nuevos (texto de 81 dígitos) sin tocar los antiguos."""

    dependencies = [("sudoku", "0002_remove_sudoku_tablero_sudoku_tablero_actual_and_more")]

    operations = [
        migrations.AddField("sudoku", "puzzle", models.CharField(default="", max_length=81, help_text="81 dígitos, 0 = casilla vacía")),
        migrations.AddField("sudoku", "solucion", models.CharField(default="", editable=False, max_length=81)),
        migrations.AddField("sudoku", "huecos", models.PositiveSmallIntegerField(default=0, editable=False)),
        migrations.AddField(
            "sudoku",
            "origen",
            models.CharField(choices=[("generado", "Generado"), ("importado", "Importado"), ("manual", "Manual")], default="manual", max_length=10),
        ),
        migrations.RenameField("sudoku", "fecha_creacion", "creado"),
    ]
