from django.core.management.base import BaseCommand

from sudoku.demo import preparar_demo


class Command(BaseCommand):
    help = "Crea o regenera la cuenta de demostración con partidas ficticias."

    def handle(self, *args, **opciones):
        user = preparar_demo()
        self.stdout.write(self.style.SUCCESS(f"Cuenta demo lista: {user.email} ({user.partidas.count()} partidas)"))
