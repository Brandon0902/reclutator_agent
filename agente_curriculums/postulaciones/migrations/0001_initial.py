import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("documentos", "0003_estados_analisis"), ("vacantes", "0005_publicacion_vacante")]
    operations = [
        migrations.CreateModel(
            name="Candidato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre_completo", models.CharField(max_length=200)),
                ("telefono_whatsapp", models.CharField(max_length=50)),
                ("correo", models.EmailField(max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Postulacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estado", models.CharField(choices=[("RECIBIDO", "Recibido"), ("EN_REVISION", "En revisión"), ("CONTACTADO", "Contactado"), ("DESCARTADO", "Descartado")], db_index=True, default="RECIBIDO", max_length=20)),
                ("consentimiento_datos", models.BooleanField(default=False)),
                ("consentimiento_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("consentimiento_version", models.CharField(default="v1", max_length=30)),
                ("ip_hash", models.CharField(blank=True, max_length=64)),
                ("user_agent_reducido", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("candidato", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="postulaciones", to="postulaciones.candidato")),
                ("documento", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="postulaciones", to="documentos.documento")),
                ("vacante", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="postulaciones", to="vacantes.vacante")),
            ],
            options={"ordering": ["-created_at"], "indexes": [models.Index(fields=["vacante", "estado"], name="postulacio_vacante_4b9027_idx"), models.Index(fields=["vacante", "created_at"], name="postulacio_vacante_3e7736_idx")], "constraints": [models.UniqueConstraint(fields=("vacante", "documento"), name="postulacion_vacante_documento_unica")]},
        ),
        migrations.AddIndex(model_name="candidato", index=models.Index(fields=["correo"], name="postulacio_correo_5c8ebf_idx")),
        migrations.AddIndex(model_name="candidato", index=models.Index(fields=["telefono_whatsapp"], name="postulacio_telefono_7c88d0_idx")),
    ]
