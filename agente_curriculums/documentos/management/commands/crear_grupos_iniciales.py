from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = "Crea los grupos iniciales y asigna permisos de documentos"
    def handle(self, *args, **options):
        perms = Permission.objects.filter(content_type__app_label="documentos")
        mapping = {"Administrador": perms, "Recursos Humanos": perms.exclude(codename__startswith="delete_"), "Solo lectura": perms.filter(codename__startswith="view_")}
        for name, selected in mapping.items():
            group, _ = Group.objects.get_or_create(name=name); group.permissions.set(selected); self.stdout.write(self.style.SUCCESS(f"Grupo listo: {name}"))
