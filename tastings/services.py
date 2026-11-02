"""
MongoDB-specific operations that go beyond the ORM.

Likes and comments are updated with atomic update operators ($addToSet,
$pull, $push) directly on the document, and the analytics are computed by the
aggregation framework inside the database instead of in Python.
"""

from bson import ObjectId
from django.db import connection
from django.utils import timezone

from .flavors import FAMILY_INDEX, FLAVOR_INDEX
from .models import PROFILE_AXES, Tasting, new_comment_id

MAX_PROFILE_DISTANCE = 10 * len(PROFILE_AXES)


def collection():
    return connection.get_collection(Tasting._meta.db_table)


def oid(value):
    return value if isinstance(value, ObjectId) else ObjectId(str(value))


# --- Likes ------------------------------------------------------------------


def set_like(tasting_id, user, liked):
    """Atomically add/remove the user's like and return the new like count."""
    operator = "$addToSet" if liked else "$pull"
    doc = collection().find_one_and_update(
        {"_id": oid(tasting_id)},
        {operator: {"likes": oid(user.pk)}},
        projection={"likes": 1},
        return_document=True,
    )
    return len(doc.get("likes", [])) if doc else 0


# --- Comments ---------------------------------------------------------------


def add_comment(tasting_id, user, text):
    comment = {
        "uid": new_comment_id(),
        "author_id": oid(user.pk),
        "author_name": user.get_username(),
        "text": text,
        "created_at": timezone.now(),
    }
    collection().update_one({"_id": oid(tasting_id)}, {"$push": {"comments": comment}})
    return comment


def remove_comment(tasting_id, comment_uid):
    result = collection().update_one(
        {"_id": oid(tasting_id)}, {"$pull": {"comments": {"uid": comment_uid}}}
    )
    return result.modified_count == 1


# --- Kindred tastes (recommendations) ---------------------------------------


def _profile_distance_expr(profile):
    return {
        "$add": [
            {"$abs": {"$subtract": [{"$ifNull": [f"$profile.{axis}", 5]}, profile.get(axis, 5)]}}
            for axis in PROFILE_AXES
        ]
    }


def similar_tastings(tasting, limit=4, cross_category=False):
    """
    Rank other public tastings by flavour overlap (Jaccard index) and
    closeness of the sensory profile — computed entirely in MongoDB.
    """
    flavors = list(tasting.flavors or [])
    profile = tasting.profile.as_dict() if tasting.profile else {}

    match = {"_id": {"$ne": oid(tasting.pk)}, "is_public": True}
    if cross_category:
        match["category"] = {"$ne": tasting.category}

    pipeline = [
        {"$match": match},
        {
            "$addFields": {
                "shared": {"$setIntersection": [{"$ifNull": ["$flavors", []]}, flavors]},
                "union_size": {"$size": {"$setUnion": [{"$ifNull": ["$flavors", []]}, flavors]}},
                "distance": _profile_distance_expr(profile),
            }
        },
        {
            "$addFields": {
                "jaccard": {"$divide": [{"$size": "$shared"}, {"$max": ["$union_size", 1]}]},
                "closeness": {"$subtract": [1, {"$divide": ["$distance", MAX_PROFILE_DISTANCE]}]},
            }
        },
        {
            "$addFields": {
                "match": {"$add": [{"$multiply": ["$jaccard", 0.6]}, {"$multiply": ["$closeness", 0.4]}]}
            }
        },
        {"$sort": {"match": -1, "score": -1}},
        {"$limit": limit},
        {"$project": {"_id": 1, "match": 1, "shared": 1}},
    ]
    ranked = list(collection().aggregate(pipeline))
    by_id = {
        str(t.pk): t
        for t in Tasting.objects.filter(pk__in=[r["_id"] for r in ranked]).select_related("author")
    }
    results = []
    for row in ranked:
        item = by_id.get(str(row["_id"]))
        if item is None:
            continue
        item.match_percent = round(row["match"] * 100)
        item.shared_flavors = [FLAVOR_INDEX[f] for f in row["shared"] if f in FLAVOR_INDEX]
        results.append(item)
    return results


# --- Almanac (site-wide statistics) -----------------------------------------


def _family_of(field):
    return {"$arrayElemAt": [{"$split": [field, ":"]}, 0]}


def almanac(match=None):
    """Every statistic for the Almanac page in one round-trip via $facet."""
    match = {"is_public": True, **(match or {})}
    avg_profile = {axis: {"$avg": f"$profile.{axis}"} for axis in PROFILE_AXES}
    pipeline = [
        {"$match": match},
        {
            "$facet": {
                "totals": [
                    {
                        "$group": {
                            "_id": None,
                            "tastings": {"$sum": 1},
                            "avg_score": {"$avg": "$score"},
                            "likes": {"$sum": {"$size": {"$ifNull": ["$likes", []]}}},
                            "comments": {"$sum": {"$size": {"$ifNull": ["$comments", []]}}},
                            "authors": {"$addToSet": "$author_id"},
                            "origins": {"$addToSet": "$origin"},
                        }
                    },
                    {
                        "$project": {
                            "_id": 0,
                            "tastings": 1,
                            "likes": 1,
                            "comments": 1,
                            "avg_score": {"$round": ["$avg_score", 1]},
                            "authors": {"$size": "$authors"},
                            "origins": {"$size": "$origins"},
                        }
                    },
                ],
                "by_category": [
                    {
                        "$group": {
                            "_id": "$category",
                            "count": {"$sum": 1},
                            "avg_score": {"$avg": "$score"},
                            **avg_profile,
                        }
                    },
                    {"$sort": {"count": -1}},
                ],
                "top_flavors": [
                    {"$unwind": "$flavors"},
                    {"$group": {"_id": "$flavors", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1, "_id": 1}},
                    {"$limit": 10},
                ],
                "families": [
                    {"$unwind": "$flavors"},
                    {"$group": {"_id": _family_of("$flavors"), "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                ],
                "score_buckets": [
                    {
                        "$bucket": {
                            "groupBy": "$score",
                            "boundaries": [50, 70, 80, 85, 90, 95, 101],
                            "default": "other",
                            "output": {"count": {"$sum": 1}},
                        }
                    }
                ],
                "top_origins": [
                    {"$match": {"origin": {"$ne": ""}}},
                    {"$group": {"_id": "$origin", "count": {"$sum": 1}, "avg_score": {"$avg": "$score"}}},
                    {"$sort": {"count": -1, "avg_score": -1}},
                    {"$limit": 6},
                ],
            }
        },
    ]
    raw = next(collection().aggregate(pipeline), {})
    return _shape_almanac(raw)


def _round_profile(row):
    return {axis: round(row.get(axis) or 0, 1) for axis in PROFILE_AXES}


def _shape_almanac(raw):
    totals = (raw.get("totals") or [{}])[0] if raw.get("totals") else {}
    labels = dict(Tasting.Category.choices)
    bucket_labels = {50: "50–69", 70: "70–79", 80: "80–84", 85: "85–89", 90: "90–94", 95: "95–100"}
    return {
        "totals": {
            "tastings": totals.get("tastings", 0),
            "avg_score": totals.get("avg_score") or 0,
            "likes": totals.get("likes", 0),
            "comments": totals.get("comments", 0),
            "authors": totals.get("authors", 0),
            "origins": totals.get("origins", 0),
        },
        "by_category": [
            {
                "category": row["_id"],
                "label": labels.get(row["_id"], row["_id"]),
                "count": row["count"],
                "avg_score": round(row["avg_score"] or 0, 1),
                "profile": _round_profile(row),
            }
            for row in raw.get("by_category", [])
        ],
        "top_flavors": [
            {**FLAVOR_INDEX[row["_id"]], "count": row["count"]}
            for row in raw.get("top_flavors", [])
            if row["_id"] in FLAVOR_INDEX
        ],
        "families": [
            {
                "id": row["_id"],
                "label": FAMILY_INDEX[row["_id"]]["label"],
                "color": FAMILY_INDEX[row["_id"]]["color"],
                "count": row["count"],
            }
            for row in raw.get("families", [])
            if row["_id"] in FAMILY_INDEX
        ],
        "score_buckets": [
            {"label": bucket_labels.get(row["_id"], str(row["_id"])), "count": row["count"]}
            for row in raw.get("score_buckets", [])
        ],
        "top_origins": [
            {"origin": row["_id"], "count": row["count"], "avg_score": round(row["avg_score"], 1)}
            for row in raw.get("top_origins", [])
        ],
    }


def palate_fingerprint(user):
    """A contributor's average profile and favourite flavour families."""
    pipeline = [
        {"$match": {"author_id": oid(user.pk)}},
        {
            "$facet": {
                "summary": [
                    {
                        "$group": {
                            "_id": None,
                            "count": {"$sum": 1},
                            "avg_score": {"$avg": "$score"},
                            "categories": {"$addToSet": "$category"},
                            **{axis: {"$avg": f"$profile.{axis}"} for axis in PROFILE_AXES},
                        }
                    }
                ],
                "families": [
                    {"$unwind": "$flavors"},
                    {"$group": {"_id": _family_of("$flavors"), "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 5},
                ],
            }
        },
    ]
    raw = next(collection().aggregate(pipeline), {})
    summary = (raw.get("summary") or [{}])[0] if raw.get("summary") else {}
    return {
        "count": summary.get("count", 0),
        "avg_score": round(summary.get("avg_score") or 0, 1),
        "categories": sorted(summary.get("categories", [])),
        "profile": _round_profile(summary),
        "families": [
            {
                "id": row["_id"],
                "label": FAMILY_INDEX[row["_id"]]["label"],
                "color": FAMILY_INDEX[row["_id"]]["color"],
                "count": row["count"],
            }
            for row in raw.get("families", [])
            if row["_id"] in FAMILY_INDEX
        ],
    }
