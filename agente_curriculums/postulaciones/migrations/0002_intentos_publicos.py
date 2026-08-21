import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("postulaciones", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="IntentoPostulacionPublica",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ip_hash", models.CharField(blank=True, max_length=64)),
                ("correo_hash", models.CharField(blank=True, max_length=64)),
                ("telefono_hash", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("vacante", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="intentos_postulacion", to="vacantes.vacante")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["ip_hash", "created_at"], name="post_int_ip_fecha_idx"),
                    models.Index(fields=["correo_hash", "created_at"], name="post_int_correo_fecha_idx"),
                    models.Index(fields=["telefono_hash", "created_at"], name="post_int_tel_fecha_idx"),
                ],
            },
        ),
    ]
