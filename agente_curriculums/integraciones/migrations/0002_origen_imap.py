from django.db import migrations, models


ORIGENES = [
    ("MANUAL", "Carga manual"),
    ("OUTLOOK", "Outlook"),
    ("WHATSAPP", "WhatsApp"),
    ("IMAP", "Correo IMAP"),
]


class Migration(migrations.Migration):
    dependencies = [("documentos", "0002_origen_imap"), ("integraciones", "0001_initial")]
    operations = [
        migrations.AlterField(model_name="mensajeexternoprocesado", name="origen", field=models.CharField(choices=ORIGENES, max_length=12)),
    ]
