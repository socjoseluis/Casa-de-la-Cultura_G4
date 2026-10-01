"""
Recalcula las vistas materializadas del dashboard.

Uso:
    python manage.py refrescar_estadisticas

Se ejecuta automáticamente al final de load_data_postgres.py y al registrar
una valoración; este comando permite lanzarlo a mano.
"""

from django.core.management.base import BaseCommand

from app.estadisticas import refrescar_estadisticas


class Command(BaseCommand):
    help = "Recalcula las vistas materializadas de estadísticas del dashboard."

    def handle(self, *args, **opciones):
        for vista, segundos in refrescar_estadisticas().items():
            self.stdout.write(f"{vista}: {segundos:.2f} s")
        self.stdout.write(self.style.SUCCESS("Estadísticas actualizadas."))
