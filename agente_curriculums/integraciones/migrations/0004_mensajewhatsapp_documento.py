import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documentos", "0003_estados_analisis"),
        ("integraciones", "0003_eventowebhook_mensajewhatsapp"),
    ]

    operations = [
        migrations.AddField(
            model_name="mensajewhatsapp",
            name="documento",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="mensajes_whatsapp", to="documentos.documento",
            ),
        ),
    ]
