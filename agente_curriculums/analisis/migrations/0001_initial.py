import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("documentos", "0003_estados_analisis")]
    operations = [
        migrations.CreateModel(
            name="RubricaEvaluacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=150)),
                ("descripcion", models.TextField(blank=True)),
                ("version", models.PositiveIntegerField(default=1)),
                ("activa", models.BooleanField(default=True)),
                ("predeterminada", models.BooleanField(default=False)),
                ("clave_predeterminada", models.CharField(blank=True, editable=False, max_length=20, null=True, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["nombre", "-version"]},
        ),
        migrations.CreateModel(
            name="ContenidoExtraido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("texto", models.TextField(blank=True)),
                ("paginas", models.PositiveIntegerField(default=0)),
                ("caracteres", models.PositiveIntegerField(default=0)),
                ("version_extractor", models.CharField(default="pymupdf-v1", max_length=30)),
                ("estado", models.CharField(choices=[("COMPLETADO", "Completado"), ("SIN_TEXTO", "Sin texto"), ("ERROR", "Error")], max_length=20)),
                ("error", models.TextField(blank=True)),
                ("extracted_at", models.DateTimeField(auto_now=True)),
                ("documento", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="contenido_extraido", to="documentos.documento")),
            ],
        ),
        migrations.CreateModel(
            name="CriterioEvaluacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=150)),
                ("descripcion", models.TextField()),
                ("peso", models.DecimalField(decimal_places=2, max_digits=5)),
                ("obligatorio", models.BooleanField(default=False)),
                ("orden", models.PositiveIntegerField(default=0)),
                ("rubrica", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="criterios", to="analisis.rubricaevaluacion")),
            ],
            options={"ordering": ["orden", "id"]},
        ),
        migrations.CreateModel(
            name="AnalisisDocumento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.PositiveIntegerField()),
                ("estado", models.CharField(choices=[("PENDIENTE", "Pendiente"), ("PROCESANDO", "Procesando"), ("COMPLETADO", "Completado"), ("ERROR", "Error"), ("SIN_TEXTO", "Sin texto")], db_index=True, default="PENDIENTE", max_length=20)),
                ("perfil", models.JSONField(blank=True, default=dict)),
                ("resumen", models.TextField(blank=True)),
                ("fortalezas", models.JSONField(blank=True, default=list)),
                ("brechas", models.JSONField(blank=True, default=list)),
                ("resultados_criterios", models.JSONField(blank=True, default=list)),
                ("puntuacion", models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=5, null=True)),
                ("modelo", models.CharField(max_length=150)),
                ("version_prompt", models.CharField(default="v1", max_length=30)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("documento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="analisis", to="documentos.documento")),
                ("rubrica", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="analisis", to="analisis.rubricaevaluacion")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(model_name="rubricaevaluacion", constraint=models.UniqueConstraint(fields=("nombre", "version"), name="rubrica_nombre_version_unica")),
        migrations.AddConstraint(model_name="criterioevaluacion", constraint=models.CheckConstraint(condition=models.Q(("peso__gt", 0), ("peso__lte", 100)), name="criterio_peso_valido")),
        migrations.AddConstraint(model_name="analisisdocumento", constraint=models.UniqueConstraint(fields=("documento", "rubrica", "numero"), name="analisis_version_unica")),
    ]
