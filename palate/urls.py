from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("tastings.api.urls")),
    path("accounts/", include("accounts.urls")),
    path("", include("tastings.urls")),
]

handler404 = "tastings.views.not_found"
