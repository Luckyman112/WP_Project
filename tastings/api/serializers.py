from django.urls import reverse
from rest_framework import serializers

from ..flavors import FLAVOR_INDEX, describe
from ..models import DETAIL_MODELS, PROFILE_AXES, Profile, Tasting

MAX_FLAVORS = 12


class ProfileSerializer(serializers.Serializer):
    sweetness = serializers.IntegerField(min_value=0, max_value=10)
    acidity = serializers.IntegerField(min_value=0, max_value=10)
    bitterness = serializers.IntegerField(min_value=0, max_value=10)
    body = serializers.IntegerField(min_value=0, max_value=10)
    finish = serializers.IntegerField(min_value=0, max_value=10)
    intensity = serializers.IntegerField(min_value=0, max_value=10)


def detail_serializer_for(model):
    """Build a serializer for one of the polymorphic `details` models."""
    meta = type("Meta", (), {"model": model, "fields": [f.name for f in model._meta.fields if not f.auto_created]})
    return type(f"{model.__name__}Serializer", (serializers.ModelSerializer,), {"Meta": meta})


DETAIL_SERIALIZERS = {category: detail_serializer_for(model) for category, model in DETAIL_MODELS.items()}


def serialize_details(tasting):
    if tasting.details is None:
        return {}
    serializer = DETAIL_SERIALIZERS.get(tasting.category)
    if serializer is None or not isinstance(tasting.details, DETAIL_MODELS[tasting.category]):
        return {}
    data = serializer(tasting.details).data
    return {key: value for key, value in data.items() if value not in (None, "")}


def comment_to_dict(comment, request=None):
    get = comment.get if isinstance(comment, dict) else lambda key: getattr(comment, key)
    user = getattr(request, "user", None)
    author_id = str(get("author_id"))
    return {
        "id": get("uid"),
        "author": get("author_name"),
        "author_url": reverse("accounts:profile", args=[get("author_name")]),
        "text": get("text"),
        "created_at": get("created_at").isoformat(),
        "can_delete": bool(user and user.is_authenticated and str(user.pk) == author_id),
    }


class CommentSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000, trim_whitespace=True)

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("A comment cannot be empty.")
        return value


class TastingSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="pk", read_only=True)
    url = serializers.SerializerMethodField()
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    author = serializers.SerializerMethodField()
    profile = ProfileSerializer(write_only=True)
    details = serializers.DictField(required=False, default=dict, write_only=True)
    flavors = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    flavor_details = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(read_only=True)
    liked = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    issue_number = serializers.CharField(read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Tasting
        fields = [
            "id", "url", "issue_number", "category", "category_label", "name", "producer",
            "origin", "score", "notes", "flavors", "flavor_details", "profile", "details",
            "is_public", "author", "like_count", "liked", "comment_count", "can_edit",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    # --- representation -----------------------------------------------------

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def get_url(self, obj):
        return obj.get_absolute_url()

    def get_author(self, obj):
        return {
            "username": obj.author.username,
            "url": reverse("accounts:profile", args=[obj.author.username]),
        }

    def get_flavor_details(self, obj):
        return describe(obj.flavors or [])

    def get_liked(self, obj):
        return obj.is_liked_by(self._user())

    def get_comment_count(self, obj):
        return len(obj.comments or [])

    def get_can_edit(self, obj):
        user = self._user()
        return bool(user and user.is_authenticated and str(obj.author_id) == str(user.pk))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["profile"] = instance.profile.as_dict() if instance.profile else {}
        data["details"] = serialize_details(instance)
        return data

    # --- validation ---------------------------------------------------------

    def validate_flavors(self, value):
        unknown = [f for f in value if f not in FLAVOR_INDEX]
        if unknown:
            raise serializers.ValidationError(f"Unknown flavours: {', '.join(unknown)}")
        unique = list(dict.fromkeys(value))
        if len(unique) > MAX_FLAVORS:
            raise serializers.ValidationError(f"Pick at most {MAX_FLAVORS} flavours.")
        return unique

    def validate(self, attrs):
        category = attrs.get("category") or getattr(self.instance, "category", None)
        if "details" in attrs or "category" in attrs:
            raw = attrs.get("details") or {}
            serializer = DETAIL_SERIALIZERS[category](data=raw)
            if not serializer.is_valid():
                raise serializers.ValidationError({"details": serializer.errors})
            attrs["details"] = serializer.validated_data
        return attrs

    # --- persistence --------------------------------------------------------

    def _apply(self, instance, validated):
        profile = validated.pop("profile", None)
        details = validated.pop("details", None)
        for field, value in validated.items():
            setattr(instance, field, value)
        if profile is not None:
            instance.profile = Profile(**{axis: profile[axis] for axis in PROFILE_AXES})
        if details is not None:
            instance.details = DETAIL_MODELS[instance.category](**details)
        instance.full_clean(exclude=["author", "profile", "details", "likes", "comments"])
        instance.save()
        return instance

    def create(self, validated_data):
        return self._apply(Tasting(author=self._user()), validated_data)

    def update(self, instance, validated_data):
        return self._apply(instance, validated_data)
