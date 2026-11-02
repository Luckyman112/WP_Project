from bson import ObjectId
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import services
from ..flavors import FAMILY_INDEX, flavor_id, wheel_payload
from ..models import Tasting
from .permissions import IsAuthorOrReadOnly
from .serializers import CommentSerializer, TastingSerializer, comment_to_dict

SORTS = {
    "newest": ["-created_at"],
    "oldest": ["created_at"],
    "score": ["-score", "-created_at"],
    "name": ["name"],
}


class TastingViewSet(viewsets.ModelViewSet):
    """
    CRUD for tastings plus nested resources.

    Query parameters for the list endpoint:
    `q`, `category` (comma separated), `family`, `flavor`, `min_score`,
    `author`, `liked=1`, `sort` (newest|oldest|score|name), `page`.
    """

    serializer_class = TastingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    lookup_value_regex = "[0-9a-f]{24}"

    def get_queryset(self):
        user = self.request.user
        visible = Q(is_public=True)
        if user.is_authenticated:
            visible |= Q(author=user)
        qs = Tasting.objects.filter(visible).select_related("author")

        if self.action != "list":
            return qs

        params = self.request.query_params
        if q := params.get("q", "").strip():
            qs = qs.filter(
                Q(name__icontains=q) | Q(producer__icontains=q) | Q(origin__icontains=q) | Q(notes__icontains=q)
            )
        if categories := [c for c in params.get("category", "").split(",") if c in Tasting.Category.values]:
            qs = qs.filter(category__in=categories)
        if (family := params.get("family")) in FAMILY_INDEX:
            notes = [flavor_id(family, note) for note in FAMILY_INDEX[family]["notes"]]
            qs = qs.filter(flavors__overlap=notes)
        if flavor := params.get("flavor"):
            qs = qs.filter(flavors__contains=[flavor])
        if (min_score := params.get("min_score", "")).isdigit():
            qs = qs.filter(score__gte=int(min_score))
        if author := params.get("author"):
            qs = qs.filter(author__username=author)
        if params.get("liked") == "1" and user.is_authenticated:
            qs = qs.filter(likes__contains=[ObjectId(str(user.pk))])
        return qs.order_by(*SORTS.get(params.get("sort"), SORTS["newest"]))

    def perform_create(self, serializer):
        serializer.save()

    # --- /tastings/{id}/like/ ----------------------------------------------

    @action(detail=True, methods=["post", "delete"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        tasting = self.get_object()
        count = services.set_like(tasting.pk, request.user, liked=request.method == "POST")
        return Response({"liked": request.method == "POST", "like_count": count})

    # --- /tastings/{id}/comments/ ------------------------------------------

    @action(detail=True, methods=["get", "post"], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, pk=None):
        tasting = self.get_object()
        if request.method == "GET":
            items = sorted(tasting.comments or [], key=lambda c: c.created_at)
            return Response([comment_to_dict(c, request) for c in items])

        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = services.add_comment(tasting.pk, request.user, serializer.validated_data["text"])
        return Response(comment_to_dict(comment, request), status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"comments/(?P<comment_id>[0-9a-f]{32})",
        permission_classes=[permissions.IsAuthenticated],
    )
    def delete_comment(self, request, pk=None, comment_id=None):
        tasting = self.get_object()
        comment = next((c for c in tasting.comments or [] if c.uid == comment_id), None)
        if comment is None:
            return Response({"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)
        is_owner = str(comment.author_id) == str(request.user.pk) or str(tasting.author_id) == str(request.user.pk)
        if not is_owner:
            return Response({"detail": "You cannot delete this comment."}, status=status.HTTP_403_FORBIDDEN)
        services.remove_comment(tasting.pk, comment_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- /tastings/{id}/similar/ -------------------------------------------

    @action(detail=True, methods=["get"])
    def similar(self, request, pk=None):
        tasting = self.get_object()
        cross = request.query_params.get("cross") == "1"
        items = services.similar_tastings(tasting, limit=4, cross_category=cross)
        data = TastingSerializer(items, many=True, context={"request": request}).data
        for row, item in zip(data, items):
            row["match_percent"] = item.match_percent
            row["shared_flavors"] = item.shared_flavors
        return Response(data)


class FlavorWheelView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(wheel_payload())


class AlmanacView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        category = request.query_params.get("category")
        match = {"category": category} if category in Tasting.Category.values else None
        return Response(services.almanac(match))


class PalateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, username):
        user = get_object_or_404(get_user_model(), username=username)
        return Response({"username": user.username, **services.palate_fingerprint(user)})
