"""
The Palate flavour wheel.

One shared taxonomy is used for every category (coffee, tea, chocolate, wine).
That is deliberate: a common vocabulary is what makes cross-category
"kindred tastes" possible — an Ethiopian coffee and a Pinot Noir can both be
`fruity:cherry` + `floral:rose`.

Flavour identifiers have the form ``"<family>:<note>"``.
"""

FLAVOR_WHEEL = [
    {
        "id": "fruity",
        "label": "Fruity",
        "color": "#B4432F",
        "notes": ["Blueberry", "Cherry", "Citrus", "Stone fruit", "Tropical", "Dried fruit"],
    },
    {
        "id": "floral",
        "label": "Floral",
        "color": "#B9798F",
        "notes": ["Jasmine", "Rose", "Chamomile", "Lavender", "Orange blossom"],
    },
    {
        "id": "sweet",
        "label": "Sweet",
        "color": "#D19A3A",
        "notes": ["Honey", "Caramel", "Vanilla", "Brown sugar", "Maple"],
    },
    {
        "id": "nutty",
        "label": "Nutty & Cocoa",
        "color": "#7A4E2D",
        "notes": ["Hazelnut", "Almond", "Cocoa", "Dark chocolate", "Peanut"],
    },
    {
        "id": "spice",
        "label": "Spice",
        "color": "#A2602B",
        "notes": ["Cinnamon", "Clove", "Black pepper", "Cardamom", "Anise"],
    },
    {
        "id": "roasted",
        "label": "Roasted",
        "color": "#4B3B33",
        "notes": ["Smoke", "Toast", "Tobacco", "Malt", "Cereal"],
    },
    {
        "id": "vegetal",
        "label": "Green & Vegetal",
        "color": "#5E6B3A",
        "notes": ["Grass", "Herbal", "Hay", "Seaweed", "Olive"],
    },
    {
        "id": "earthy",
        "label": "Earthy",
        "color": "#6E6656",
        "notes": ["Mushroom", "Leather", "Wet stone", "Forest floor", "Mineral"],
    },
]


def slugify_note(note):
    return note.lower().replace(" ", "-")


def flavor_id(family_id, note):
    return f"{family_id}:{slugify_note(note)}"


FLAVOR_INDEX = {
    flavor_id(family["id"], note): {
        "id": flavor_id(family["id"], note),
        "label": note,
        "family": family["id"],
        "family_label": family["label"],
        "color": family["color"],
    }
    for family in FLAVOR_WHEEL
    for note in family["notes"]
}

FAMILY_INDEX = {family["id"]: family for family in FLAVOR_WHEEL}


def wheel_payload():
    """Serializable wheel used by the front-end SVG component."""
    return [
        {
            "id": family["id"],
            "label": family["label"],
            "color": family["color"],
            "notes": [
                {"id": flavor_id(family["id"], note), "label": note} for note in family["notes"]
            ],
        }
        for family in FLAVOR_WHEEL
    ]


def describe(flavor_ids):
    return [FLAVOR_INDEX[f] for f in flavor_ids if f in FLAVOR_INDEX]
