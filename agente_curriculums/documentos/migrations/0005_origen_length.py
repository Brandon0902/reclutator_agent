from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documentos", "0004_formulario_web")]
    operations = [
        migrations.AlterField(
            model_name="intentorecepciondocumento",
            name="origen",
            field=models.CharField(choices=[("MANUAL", "Carga manual"), ("OUTLOOK", "Outlook"), ("WHATSAPP", "WhatsApp"), ("IMAP", "Correo IMAP"), ("FORMULARIO_WEB", "Formulario web")], max_length=20),
        ),
    ]
