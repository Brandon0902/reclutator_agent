from django.db import migrations, models


ORIGENES = [
    ("MANUAL", "Carga manual"),
    ("OUTLOOK", "Outlook"),
    ("WHATSAPP", "WhatsApp"),
    ("IMAP", "Correo IMAP"),
]


class Migration(migrations.Migration):
    dependencies = [("documentos", "0001_initial")]
    operations = [
        migrations.AlterField(model_name="documento", name="origen", field=models.CharField(choices=ORIGENES, max_length=12)),
        migrations.AlterField(model_name="intentorecepciondocumento", name="origen", field=models.CharField(choices=ORIGENES, max_length=12)),
    ]
