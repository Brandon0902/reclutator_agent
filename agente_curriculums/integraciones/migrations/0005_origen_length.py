from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("integraciones", "0004_mensajewhatsapp_documento")]
    operations = [
        migrations.AlterField(
            model_name="mensajeexternoprocesado",
            name="origen",
            field=models.CharField(choices=[("MANUAL", "Carga manual"), ("OUTLOOK", "Outlook"), ("WHATSAPP", "WhatsApp"), ("IMAP", "Correo IMAP"), ("FORMULARIO_WEB", "Formulario web")], max_length=20),
        ),
    ]
