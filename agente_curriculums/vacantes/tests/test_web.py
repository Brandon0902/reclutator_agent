import pytest
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders


pytestmark = pytest.mark.django_db


def test_workspace_requiere_autenticacion(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/login/")


def test_login_y_workspace_cargan_recursos_del_chat(client):
    get_user_model().objects.create_user(username="reclutador-web", password="clave-segura-123")
    respuesta = client.post("/login/", {"username": "reclutador-web", "password": "clave-segura-123"})
    assert respuesta.status_code == 302 and respuesta.url == "/"
    pagina = client.get("/")
    contenido = pagina.content.decode()
    assert pagina.status_code == 200
    assert 'id="new-job"' in contenido
    assert 'id="message-form"' in contenido
    assert 'id="ranking-list"' in contenido
    assert pagina.cookies.get("csrftoken")
    assert finders.find("vacantes/app.css")
    assert finders.find("vacantes/app.js")


def test_login_incorrecto_muestra_error(client):
    respuesta = client.post("/login/", {"username": "nadie", "password": "incorrecta"})
    assert respuesta.status_code == 200
    assert "Usuario o contraseña incorrectos" in respuesta.content.decode()
