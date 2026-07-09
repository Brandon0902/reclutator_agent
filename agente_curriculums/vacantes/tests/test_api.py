import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from vacantes.models import EstadoTarea, EstadoVacante, Vacante


pytestmark = pytest.mark.django_db


def cliente_de(username):
    usuario = get_user_model().objects.create_user(username=username, password="clave-segura")
    cliente = APIClient()
    cliente.force_authenticate(usuario)
    return cliente, usuario


def test_crear_listar_detallar_y_conservar_orden_de_mensajes():
    cliente, _ = cliente_de("reclutador")
    respuesta = cliente.post("/api/vacantes/", {"mensaje": "Busco una persona desarrolladora Python"}, format="json")
    assert respuesta.status_code == 202
    vacante_id = respuesta.json()["id"]
    Vacante.objects.get(pk=vacante_id).tareas_conversacion.update(estado=EstadoTarea.COMPLETADA)
    assert cliente.post(f"/api/vacantes/{vacante_id}/mensajes/", {"contenido": "Django es obligatorio"}, format="json").status_code == 202
    mensajes = cliente.get(f"/api/vacantes/{vacante_id}/mensajes/").json()
    assert [item["contenido"] for item in mensajes] == ["Busco una persona desarrolladora Python", "Django es obligatorio"]
    assert cliente.get("/api/vacantes/").json()["count"] == 1
    assert cliente.get(f"/api/vacantes/{vacante_id}/").status_code == 200


def test_aislamiento_por_usuario_y_autenticacion():
    cliente_a, usuario_a = cliente_de("a")
    cliente_b, _ = cliente_de("b")
    vacante = Vacante.objects.create(propietario=usuario_a)
    assert cliente_b.get(f"/api/vacantes/{vacante.id}/").status_code == 404
    assert cliente_b.get(f"/api/vacantes/{vacante.id}/mensajes/").status_code == 404
    assert APIClient().get("/api/vacantes/").status_code in {401, 403}


def test_rechaza_mensaje_vacio_y_conversacion_confirmada():
    cliente, usuario = cliente_de("reclutador")
    vacante = Vacante.objects.create(propietario=usuario)
    assert cliente.post(f"/api/vacantes/{vacante.id}/mensajes/", {"contenido": "   "}, format="json").status_code == 400
    vacante.estado = EstadoVacante.CONFIRMADA
    vacante.save(update_fields=["estado"])
    assert cliente.post(f"/api/vacantes/{vacante.id}/mensajes/", {"contenido": "Cambiar"}, format="json").status_code == 400


def test_rechaza_otro_turno_mientras_el_agente_esta_procesando():
    cliente, _ = cliente_de("turnos")
    vacante_id = cliente.post("/api/vacantes/", {"mensaje": "Busco Python"}, format="json").json()["id"]
    respuesta = cliente.post(f"/api/vacantes/{vacante_id}/mensajes/", {"contenido": "También Django"}, format="json")
    assert respuesta.status_code == 400
