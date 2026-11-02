from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from . import services
from .api.serializers import TastingSerializer
from .flavors import wheel_payload
from .models import DETAIL_MODELS, PROFILE_AXES, Tasting


def _visible(user):
    q = Q(is_public=True)
    if user.is_authenticated:
        q |= Q(author=user)
    return Tasting.objects.filter(q).select_related("author")


def _get_visible_or_404(request, pk):
    try:
        return _visible(request.user).get(pk=pk)
    except (Tasting.DoesNotExist, ValueError, TypeError) as exc:
        raise Http404("Tasting not found") from exc


def home(request):
    public = Tasting.objects.filter(is_public=True).select_related("author")
    month_ago = timezone.now() - timezone.timedelta(days=30)
    featured = public.filter(created_at__gte=month_ago).order_by("-score").first() or public.order_by("-score").first()
    latest = list(public.exclude(pk=getattr(featured, "pk", None)).order_by("-created_at")[:6])

    pairing = None
    if featured:
        kindred = services.similar_tastings(featured, limit=1, cross_category=True)
        if kindred:
            pairing = {"a": featured, "b": kindred[0]}

    return render(request, "tastings/home.html", {
        "featured": featured,
        "latest": latest,
        "pairing": pairing,
        "totals": services.almanac()["totals"],
    })


def journal(request):
    return render(request, "tastings/journal.html", {
        "categories": Tasting.Category.choices,
        "wheel": wheel_payload(),
    })


def detail(request, pk):
    tasting = _get_visible_or_404(request, pk)
    data = TastingSerializer(tasting, context={"request": request}).data
    return render(request, "tastings/detail.html", {
        "tasting": tasting,
        "data": data,
        "details": _labelled_details(tasting, data["details"]),
    })


def _labelled_details(tasting, details):
    model = DETAIL_MODELS[tasting.category]
    rows = []
    for name, value in details.items():
        field = model._meta.get_field(name)
        if field.choices:
            value = dict(field.choices).get(value, value)
        rows.append((field.verbose_name.capitalize(), value))
    return rows


def _composer_context(tasting=None):
    detail_schema = {
        category: [
            {
                "name": f.name,
                "label": f.verbose_name.capitalize(),
                "type": "select" if f.choices else ("number" if f.get_internal_type() not in {"CharField"} else "text"),
                "choices": [{"value": v, "label": l} for v, l in f.choices] if f.choices else [],
            }
            for f in model._meta.fields
            if not f.auto_created
        ]
        for category, model in DETAIL_MODELS.items()
    }
    return {
        "tasting": tasting,
        "categories": Tasting.Category.choices,
        "axes": PROFILE_AXES,
        "wheel": wheel_payload(),
        "detail_schema": detail_schema,
        "origins": sorted({o for o in Tasting.objects.values_list("origin", flat=True) if o}),
    }


@login_required
def create(request):
    return render(request, "tastings/composer.html", _composer_context())


@login_required
def edit(request, pk):
    tasting = _get_visible_or_404(request, pk)
    if str(tasting.author_id) != str(request.user.pk):
        raise PermissionDenied
    context = _composer_context(tasting)
    context["initial"] = TastingSerializer(tasting, context={"request": request}).data
    return render(request, "tastings/composer.html", context)


def compare(request):
    options = [
        {"id": str(t.pk), "name": t.name, "category": t.get_category_display()}
        for t in _visible(request.user).order_by("name")[:300]
    ]
    return render(request, "tastings/compare.html", {
        "options": options,
        "a": request.GET.get("a", ""),
        "b": request.GET.get("b", ""),
    })


def almanac(request):
    return render(request, "tastings/almanac.html", {"categories": Tasting.Category.choices})


def not_found(request, exception=None):
    return render(request, "404.html", status=404)


