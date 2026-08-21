from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("vacantes", "0003_ejecucionvacante_evaluacionvacante_and_more")]

    operations = [
        migrations.AddField(
            model_name="ejecucionvacante",
            name="omitidos",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="evaluacionvacante",
            name="motivo_omision",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="evaluacionvacante",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("PROCESANDO", "Procesando"),
                    ("COMPLETADA", "Completada"),
                    ("SIN_TEXTO", "Sin texto"),
                    ("OMITIDA_NO_RELEVANTE", "Omitida: no relevante"),
                    ("ERROR", "Error"),
                ],
                db_index=True,
                default="PENDIENTE",
                max_length=20,
            ),
        ),
    ]
