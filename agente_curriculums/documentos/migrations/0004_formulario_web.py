from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documentos", "0003_estados_analisis")]
    operations = [
        migrations.AlterField(
            model_name="documento",
            name="origen",
            field=models.CharField(choices=[("MANUAL", "Carga manual"), ("OUTLOOK", "Outlook"), ("WHATSAPP", "WhatsApp"), ("IMAP", "Correo IMAP"), ("FORMULARIO_WEB", "Formulario web")], max_length=20),
        ),
    ]
