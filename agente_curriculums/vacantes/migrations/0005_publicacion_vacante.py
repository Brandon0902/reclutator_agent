import uuid

from django.db import migrations, models


def asignar_slugs_publicos(apps, schema_editor):
    Vacante = apps.get_model("vacantes", "Vacante")
    for vacante in Vacante.objects.filter(public_slug__isnull=True).iterator():
        vacante.public_slug = uuid.uuid4()
        vacante.save(update_fields=["public_slug"])


class Migration(migrations.Migration):
    dependencies = [("vacantes", "0004_prefiltro_relevancia")]
    operations = [
        migrations.AddField(
            model_name="vacante",
            name="public_slug",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(asignar_slugs_publicos, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="vacante",
            name="public_slug",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(model_name="vacante", name="publicada", field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name="vacante", name="fecha_cierre", field=models.DateTimeField(blank=True, null=True)),
    ]
