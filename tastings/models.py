"""
Tasting documents.

A single MongoDB document holds everything that is read together on the
article page: the sensory profile, the category-specific details, the list of
flavours, likes and comments. This avoids joins and is the main argument for
choosing a document database for this application.

Example document in the `tastings_tasting` collection::

    {
      "_id": ObjectId("..."),
      "author_id": ObjectId("..."),
      "category": "coffee",
      "name": "Guji Natural",
      "score": 91,
      "flavors": ["fruity:blueberry", "floral:jasmine"],
      "profile": {"sweetness": 7, "acidity": 8, ...},
      "details": {"process": "natural", "roast": "light", ...},   # differs per category
      "likes": [ObjectId("..."), ...],
      "comments": [{"id": "...", "author_name": "mira", "text": "...", ...}],
      ...
    }
"""

import uuid

from bson import ObjectId
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django_mongodb_backend.fields import (
    ArrayField,
    EmbeddedModelArrayField,
    EmbeddedModelField,
    ObjectIdField,
    PolymorphicEmbeddedModelField,
)
from django_mongodb_backend.models import EmbeddedModel

PROFILE_AXES = ["sweetness", "acidity", "bitterness", "body", "finish", "intensity"]


def axis_field():
    return models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(0), MaxValueValidator(10)]
    )


class Profile(EmbeddedModel):
    """Six-axis sensory profile, each axis from 0 to 10 (drawn as a radar)."""

    sweetness = axis_field()
    acidity = axis_field()
    bitterness = axis_field()
    body = axis_field()
    finish = axis_field()
    intensity = axis_field()

    def as_dict(self):
        return {axis: getattr(self, axis) for axis in PROFILE_AXES}


# --- Category-specific details (polymorphic embedded documents) -------------


class CoffeeDetails(EmbeddedModel):
    PROCESSES = [("washed", "Washed"), ("natural", "Natural"), ("honey", "Honey"), ("anaerobic", "Anaerobic")]
    ROASTS = [("light", "Light"), ("medium", "Medium"), ("dark", "Dark")]
    BREWS = [("espresso", "Espresso"), ("filter", "Filter"), ("aeropress", "AeroPress"), ("french-press", "French press"), ("moka", "Moka pot")]

    process = models.CharField(max_length=20, choices=PROCESSES, blank=True)
    roast = models.CharField(max_length=20, choices=ROASTS, blank=True)
    brew_method = models.CharField(max_length=20, choices=BREWS, blank=True)
    altitude_m = models.PositiveIntegerField(null=True, blank=True)
    varietal = models.CharField(max_length=60, blank=True)


class TeaDetails(EmbeddedModel):
    TYPES = [("green", "Green"), ("black", "Black"), ("oolong", "Oolong"), ("white", "White"), ("puerh", "Pu-erh"), ("herbal", "Herbal")]

    tea_type = models.CharField(max_length=20, choices=TYPES, blank=True)
    water_temp_c = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(100)])
    steep_seconds = models.PositiveIntegerField(null=True, blank=True)
    infusions = models.PositiveSmallIntegerField(null=True, blank=True)
    harvest = models.CharField(max_length=40, blank=True)


class ChocolateDetails(EmbeddedModel):
    TYPES = [("dark", "Dark"), ("milk", "Milk"), ("white", "White"), ("raw", "Raw")]

    cocoa_percent = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(100)])
    chocolate_type = models.CharField(max_length=20, choices=TYPES, blank=True)
    bean = models.CharField(max_length=60, blank=True)
    texture = models.CharField(max_length=60, blank=True)


class WineDetails(EmbeddedModel):
    STYLES = [("red", "Red"), ("white", "White"), ("rose", "Rosé"), ("orange", "Orange"), ("sparkling", "Sparkling")]

    style = models.CharField(max_length=20, choices=STYLES, blank=True)
    grape = models.CharField(max_length=60, blank=True)
    vintage = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    abv = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)


DETAIL_MODELS = {
    "coffee": CoffeeDetails,
    "tea": TeaDetails,
    "chocolate": ChocolateDetails,
    "wine": WineDetails,
}


class Comment(EmbeddedModel):
    """A comment embedded in its tasting document (no separate collection)."""

    uid = models.CharField(max_length=32, default="")
    author_id = ObjectIdField()
    author_name = models.CharField(max_length=150)
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(default=timezone.now)


def new_comment_id():
    return uuid.uuid4().hex


# --- The tasting document ---------------------------------------------------


class Tasting(models.Model):
    class Category(models.TextChoices):
        COFFEE = "coffee", "Coffee"
        TEA = "tea", "Tea"
        CHOCOLATE = "chocolate", "Chocolate"
        WINE = "wine", "Wine"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tastings")
    category = models.CharField(max_length=20, choices=Category.choices)
    name = models.CharField(max_length=120)
    producer = models.CharField(max_length=120, blank=True)
    origin = models.CharField(max_length=80, blank=True)
    score = models.PositiveSmallIntegerField(validators=[MinValueValidator(50), MaxValueValidator(100)])
    notes = models.TextField(max_length=4000, blank=True)
    flavors = ArrayField(models.CharField(max_length=60), default=list, blank=True)
    profile = EmbeddedModelField(Profile)
    details = PolymorphicEmbeddedModelField(list(DETAIL_MODELS.values()), null=True, blank=True)
    likes = ArrayField(ObjectIdField(), default=list, blank=True)
    comments = EmbeddedModelArrayField(Comment, default=list, blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "-created_at"]),
            models.Index(fields=["-score"]),
            models.Index(fields=["author", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def get_absolute_url(self):
        return reverse("tastings:detail", args=[str(self.pk)])

    @property
    def issue_number(self):
        """Editorial 'No. 042' label derived from the ObjectId's incrementing counter."""
        return f"{int(str(self.pk)[-6:], 16) % 1000:03d}"

    @property
    def like_count(self):
        return len(self.likes or [])

    def is_liked_by(self, user):
        return bool(user and user.is_authenticated and ObjectId(str(user.pk)) in (self.likes or []))
