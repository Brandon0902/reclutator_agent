from django.core.management.base import BaseCommand

from vacantes.models import EstadoTarea, TareaConversacion
from vacantes.services import procesar_tarea_conversacion


class Command(BaseCommand):
    help = "Procesa tareas conversacionales pendientes"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=2)

    def handle(self, *args, **options):
        ids = list(TareaConversacion.objects.filter(estado=EstadoTarea.PENDIENTE).order_by("created_at").values_list("id", flat=True)[:options["limit"]])
        completadas = errores = 0
        for tarea_id in ids:
            tarea = procesar_tarea_conversacion(tarea_id)
            completadas += tarea.estado == EstadoTarea.COMPLETADA
            errores += tarea.estado == EstadoTarea.ERROR
        self.stdout.write(self.style.SUCCESS(f"Conversaciones completadas: {completadas} | Errores: {errores}"))
