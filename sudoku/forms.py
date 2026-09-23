from django import forms

from . import motor
from .models import Sudoku


class SudokuAdminForm(forms.ModelForm):
    """Alta de sudokus en el admin: valida que tenga solución única y calcula su dificultad."""

    calcular_dificultad = forms.BooleanField(
        required=False,
        initial=True,
        label="Calcular la dificultad automáticamente",
        help_text="Desmárcalo para usar la dificultad elegida arriba.",
    )

    class Meta:
        model = Sudoku
        fields = ["puzzle", "dificultad", "origen"]
        widgets = {"puzzle": forms.Textarea(attrs={"rows": 9, "cols": 40})}
        help_texts = {
            "puzzle": "81 dígitos (0 o . para las vacías) o una lista JSON de 9 filas de 9 números.",
        }

    def clean_puzzle(self):
        try:
            celdas = motor.desde_texto(self.cleaned_data["puzzle"])
            motor.solucion_unica(celdas)
        except motor.TableroInvalido as e:
            raise forms.ValidationError(str(e))
        return motor.a_texto(celdas)

    def save(self, commit=True):
        sudoku = super().save(commit=False)
        sudoku.completar_desde_puzzle(calcular_dificultad=self.cleaned_data.get("calcular_dificultad"))
        if commit:
            sudoku.save()
        return sudoku
