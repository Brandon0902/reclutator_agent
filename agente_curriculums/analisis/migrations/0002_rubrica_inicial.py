from django.db import migrations


def crear_rubrica(apps, schema_editor):
    Rubrica = apps.get_model("analisis", "RubricaEvaluacion")
    Criterio = apps.get_model("analisis", "CriterioEvaluacion")
    rubrica, creada = Rubrica.objects.get_or_create(
        nombre="Evaluación general",
        version=1,
        defaults={
            "descripcion": "Rúbrica inicial configurable para ordenar currículums como apoyo a revisión humana.",
            "activa": True,
            "predeterminada": True,
            "clave_predeterminada": "DEFAULT",
        },
    )
    if creada:
        Criterio.objects.bulk_create([
            Criterio(rubrica=rubrica, nombre="Experiencia relevante", descripcion="Experiencia demostrable y relación con responsabilidades profesionales.", peso=35, orden=1),
            Criterio(rubrica=rubrica, nombre="Habilidades", descripcion="Habilidades técnicas y profesionales respaldadas por evidencia.", peso=30, orden=2),
            Criterio(rubrica=rubrica, nombre="Educación y certificaciones", descripcion="Formación y certificaciones pertinentes.", peso=20, orden=3),
            Criterio(rubrica=rubrica, nombre="Logros y claridad", descripcion="Logros verificables, resultados y claridad del currículum.", peso=15, orden=4),
        ])


class Migration(migrations.Migration):
    dependencies = [("analisis", "0001_initial")]
    operations = [migrations.RunPython(crear_rubrica, migrations.RunPython.noop)]
