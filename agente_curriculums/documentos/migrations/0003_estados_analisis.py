from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documentos", "0002_origen_imap")]
    operations = [
        migrations.AlterField(
            model_name="documento",
            name="estado",
            field=models.CharField(
                choices=[
                    ("RECIBIDO", "Recibido"),
                    ("PENDIENTE_ANALISIS", "Pendiente de análisis"),
                    ("DUPLICADO", "Duplicado"),
                    ("FORMATO_INVALIDO", "Formato inválido"),
                    ("ERROR_DESCARGA", "Error de descarga"),
                    ("ERROR_ALMACENAMIENTO", "Error de almacenamiento"),
                    ("EN_ANALISIS", "En análisis"),
                    ("ANALIZADO", "Analizado"),
                    ("ERROR_ANALISIS", "Error de análisis"),
                    ("SIN_TEXTO", "Sin texto analizable"),
                ],
                db_index=True,
                default="PENDIENTE_ANALISIS",
                max_length=30,
            ),
        ),
    ]
