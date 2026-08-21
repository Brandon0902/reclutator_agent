import django.db.models.deletion
from django.db import migrations, models


def completar_vacante_interes(apps, schema_editor):
    Postulacion = apps.get_model("postulaciones", "Postulacion")
    for postulacion in Postulacion.objects.select_related("vacante").iterator():
        postulacion.vacante_interes = postulacion.vacante.titulo or f"Vacante #{postulacion.vacante_id}"
        postulacion.save(update_fields=["vacante_interes"])


class Migration(migrations.Migration):
    dependencies = [("postulaciones", "0002_intentos_publicos")]
    operations = [
        migrations.AddField(
            model_name="postulacion",
            name="vacante_interes",
            field=models.CharField(db_index=True, default="", max_length=200),
            preserve_default=False,
        ),
        migrations.RunPython(completar_vacante_interes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="postulacion",
            name="vacante",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="postulaciones", to="vacantes.vacante"),
        ),
        migrations.AlterField(
            model_name="intentopostulacionpublica",
            name="vacante",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="intentos_postulacion", to="vacantes.vacante"),
        ),
    ]
