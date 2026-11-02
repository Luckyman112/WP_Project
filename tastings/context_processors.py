from django.utils import timezone

from .models import Tasting

FOUNDED_YEAR = 2025


def masthead(request):
    """Editorial masthead line shown on every page: volume, issue, date."""
    now = timezone.localtime()
    return {
        "masthead": {
            "volume": now.year - FOUNDED_YEAR + 1,
            "issue": now.month,
            "date": now,
        },
        "nav_categories": Tasting.Category.choices,
    }
