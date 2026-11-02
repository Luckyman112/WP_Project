from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("tastings", views.TastingViewSet, basename="tasting")

app_name = "api"

urlpatterns = [
    path("", include(router.urls)),
    path("flavors/", views.FlavorWheelView.as_view(), name="flavors"),
    path("almanac/", views.AlmanacView.as_view(), name="almanac"),
    path("users/<str:username>/palate/", views.PalateView.as_view(), name="palate"),
]
