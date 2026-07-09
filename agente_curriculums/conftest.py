import pytest


@pytest.fixture(autouse=True)
def media_temporal(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def usuario(django_user_model):
    return django_user_model.objects.create_user("rrhh", password="secret")


@pytest.fixture
def pdf():
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"
