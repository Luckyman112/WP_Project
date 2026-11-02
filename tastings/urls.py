from django.urls import path, register_converter

from . import views
from .converters import ObjectIdConverter

register_converter(ObjectIdConverter, "oid")

app_name = "tastings"

urlpatterns = [
    path("", views.home, name="home"),
    path("journal/", views.journal, name="journal"),
    path("tastings/new/", views.create, name="create"),
    path("tastings/<oid:pk>/", views.detail, name="detail"),
    path("tastings/<oid:pk>/edit/", views.edit, name="edit"),
    path("compare/", views.compare, name="compare"),
    path("almanac/", views.almanac, name="almanac"),
]
