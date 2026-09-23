from django.db import migrations

MIN_HUECOS = 30  # por debajo, el sudoku es casi un tablero resuelto


def convertir(apps, schema_editor):
    """Paso 2 de 3: pasa los tableros JSON al formato nuevo, recalcula la dificultad
    y borra los que no tienen solución única o son demasiado fáciles."""
    from sudoku import motor

    Sudoku = apps.get_model("sudoku", "Sudoku")
    for s in Sudoku.objects.all():
        try:
            celdas = motor.desde_texto(s.tablero_inicial)
            solucion = motor.solucion_unica(celdas)
        except motor.TableroInvalido:
            s.delete()
            continue
        if celdas.count(0) < MIN_HUECOS:
            s.delete()
            continue
        s.puzzle = motor.a_texto(celdas)
        s.solucion = motor.a_texto(solucion)
        s.huecos = celdas.count(0)
        s.dificultad = motor.calificar(celdas)
        s.origen = "importado" if (s.nombre or "").startswith("Sudoku HF") else "manual"
        s.save()


class Migration(migrations.Migration):
    dependencies = [("sudoku", "0003_campos_nuevos")]
    operations = [migrations.RunPython(convertir, migrations.RunPython.noop)]
