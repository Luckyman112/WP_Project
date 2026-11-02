from django.contrib import admin

from .models import Tasting


@admin.register(Tasting)
class TastingAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "score", "author", "is_public", "created_at"]
    list_filter = ["category", "is_public"]
    search_fields = ["name", "producer", "origin"]
