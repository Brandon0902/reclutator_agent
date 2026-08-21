from rest_framework.permissions import BasePermission
from django.db.models import Q


def es_admin_global(user):
    return bool(user.is_superuser or user.groups.filter(name="Administrador").exists())


def es_rh(user):
    return bool(user and user.is_authenticated and (
        user.is_staff or es_admin_global(user) or
        user.groups.filter(name__in=["Recursos Humanos", "Solo lectura"]).exists()
    ))


def puede_cambiar(user):
    return bool(es_admin_global(user) or user.is_staff or user.groups.filter(name="Recursos Humanos").exists())


def limitar_postulaciones(queryset, user):
    if es_admin_global(user):
        return queryset
    return queryset.filter(Q(vacante__propietario=user) | Q(vacante__isnull=True))


class EsRH(BasePermission):
    message = "No tienes permiso para consultar postulaciones."

    def has_permission(self, request, view):
        return es_rh(request.user)
