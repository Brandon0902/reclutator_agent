from django.db import migrations, models
import django.utils.timezone
class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.CreateModel(name="MensajeExternoProcesado", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("origen", models.CharField(choices=[("MANUAL", "Carga manual"), ("OUTLOOK", "Outlook"), ("WHATSAPP", "WhatsApp")], max_length=12)), ("id_mensaje", models.CharField(max_length=255)), ("fecha_procesamiento", models.DateTimeField(default=django.utils.timezone.now)), ("estado", models.CharField(default="PROCESADO", max_length=30)), ("error", models.TextField(blank=True)), ("metadata", models.JSONField(blank=True, default=dict))], options={"constraints": [models.UniqueConstraint(fields=("origen", "id_mensaje"), name="mensaje_origen_unico")]})]
