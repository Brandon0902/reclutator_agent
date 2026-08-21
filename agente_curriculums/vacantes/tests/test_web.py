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
    assert 'class="rubric-dashboard"' in contenido
    assert 'id="required-total"' in contenido
    assert 'id="rubric-distribution"' in contenido
    assert 'id="ranking-list"' in contenido
    assert pagina.cookies.get("csrftoken")
    assert finders.find("vacantes/app.css")
    assert finders.find("vacantes/app.js")
    assert finders.find("vacantes/jmabauen-icon.png")
    assert "vacantes/jmabauen-icon.png" in contenido
    assert "rubric-distribution" in open(finders.find("vacantes/app.js"), encoding="utf-8").read()


def test_modal_nueva_vacante_se_puede_cerrar_sin_validar_textarea(client):
    get_user_model().objects.create_user(username="reclutador-modal", password="clave-segura-123")
    client.login(username="reclutador-modal", password="clave-segura-123")

    pagina = client.get("/")
    contenido = pagina.content.decode()
    app_js = finders.find("vacantes/app.js")

    assert 'id="new-job-form" novalidate' in contenido
    assert 'id="new-job-close" type="button" formnovalidate' in contenido
    assert 'id="create-job" type="submit"' in contenido
    assert 'id="new-job-message" rows="7" maxlength="10000"' in contenido
    assert 'id="new-job-message" rows="7" maxlength="10000" placeholder' in contenido
    assert app_js
    js = open(app_js, encoding="utf-8").read()
    assert "$('new-job-close').onclick" in js
    assert "Describe la vacante antes de iniciar" in js


def test_login_incorrecto_muestra_error(client):
    respuesta = client.post("/login/", {"username": "nadie", "password": "incorrecta"})
    assert respuesta.status_code == 200
    assert "Usuario o contraseña incorrectos" in respuesta.content.decode()
