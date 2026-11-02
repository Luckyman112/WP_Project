import json
import re

from django import template
from django.utils.safestring import mark_safe

from ..flavors import FLAVOR_INDEX

register = template.Library()

VERDICTS = [
    (95, "Transcendent"),
    (90, "Outstanding"),
    (85, "Excellent"),
    (80, "Very good"),
    (70, "Good"),
    (0, "Curious"),
]


@register.filter
def verdict(score):
    """Translate a 50–100 score into the journal's verdict vocabulary."""
    score = int(score or 0)
    return next(word for threshold, word in VERDICTS if score >= threshold)


@register.filter
def standfirst(text, max_chars=160):
    """First sentence of the tasting notes, used as an editorial standfirst."""
    if not text:
        return ""
    first = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
    return first if len(first) <= max_chars else first[: max_chars - 1].rstrip() + "…"


@register.filter
def rest_of(text):
    """Everything after the standfirst sentence."""
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


@register.simple_tag(takes_context=True)
def nav_active(context, *url_names):
    match = getattr(context.get("request"), "resolver_match", None)
    return mark_safe('aria-current="page"') if match and match.view_name in url_names else ""


@register.filter
def as_json(value):
    """Serialize to JSON for use in a (auto-escaped) data attribute."""
    if hasattr(value, "as_dict"):
        value = value.as_dict()
    return json.dumps(value, default=str)


@register.filter
def flavor_color(flavor_id):
    return FLAVOR_INDEX.get(flavor_id, {}).get("color", "currentColor")
