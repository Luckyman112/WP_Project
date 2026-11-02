"""
Populate the database with demo contributors and tastings.

    python manage.py seed          # adds demo data if the journal is empty
    python manage.py seed --reset  # wipes tastings and demo users first
"""

import random

from bson import ObjectId
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from tastings.models import DETAIL_MODELS, Comment, Profile, Tasting, new_comment_id

DEMO_PASSWORD = "palate-demo-2026"
DEMO_USERS = ["mira", "oskar", "lena", "demo"]

# (name, producer, origin, score, flavors, profile[sweet, acid, bitter, body, finish, intensity], details, notes)
TASTINGS = {
    "coffee": [
        ("Guji Natural", "Kalve Roasters", "Ethiopia", 92, ["fruity:blueberry", "floral:jasmine", "sweet:honey"], [7, 8, 2, 5, 7, 7],
         {"process": "natural", "roast": "light", "brew_method": "filter", "altitude_m": 2100, "varietal": "Heirloom"},
         "Opens with a wave of blueberry jam and bergamot. As it cools, jasmine climbs out of the cup and the finish turns to wildflower honey. A cup that asks you to slow down."),
        ("Huila Pink Bourbon", "Rocket Bean", "Colombia", 89, ["fruity:citrus", "sweet:caramel", "floral:rose"], [6, 7, 3, 5, 6, 6],
         {"process": "washed", "roast": "light", "brew_method": "aeropress", "altitude_m": 1750, "varietal": "Pink Bourbon"},
         "Blood orange brightness carried on a soft caramel body. Rose petals on the exhale."),
        ("Cerrado Pulped", "Mazais Grauds", "Brazil", 84, ["nutty:peanut", "nutty:cocoa", "sweet:brown-sugar"], [6, 3, 4, 7, 5, 5],
         {"process": "honey", "roast": "medium", "brew_method": "espresso", "altitude_m": 1100, "varietal": "Yellow Catuaí"},
         "The comfort-food espresso: roasted peanut, milk chocolate, brown sugar. Unchallenging and exactly right at 8 a.m."),
        ("Kiambu AA", "Kalve Roasters", "Kenya", 93, ["fruity:cherry", "fruity:citrus", "spice:black-pepper"], [5, 9, 3, 6, 8, 8],
         {"process": "washed", "roast": "light", "brew_method": "filter", "altitude_m": 1800, "varietal": "SL28"},
         "Electric. Redcurrant and grapefruit with a peppery snap on the finish. Divisive at the table, and that is a compliment."),
        ("Sumatra Wet-Hulled", "Barista Lab", "Indonesia", 81, ["earthy:forest-floor", "roasted:tobacco", "spice:clove"], [3, 2, 6, 9, 7, 8],
         {"process": "natural", "roast": "dark", "brew_method": "french-press", "altitude_m": 1400, "varietal": "Ateng"},
         "Damp cedar, pipe tobacco and clove. Heavy, syrupy body. A rainy-afternoon coffee."),
        ("Gesha Village Lot 74", "Rocket Bean", "Ethiopia", 96, ["floral:jasmine", "floral:orange-blossom", "fruity:stone-fruit"], [8, 7, 1, 4, 9, 7],
         {"process": "washed", "roast": "light", "brew_method": "filter", "altitude_m": 2000, "varietal": "Gesha"},
         "Tea-like and translucent. Orange blossom, white peach, jasmine — the finish lingers for a full minute."),
        ("Anaerobic Catuaí", "Mazais Grauds", "Costa Rica", 87, ["fruity:tropical", "sweet:vanilla", "fruity:dried-fruit"], [8, 6, 2, 6, 6, 8],
         {"process": "anaerobic", "roast": "light", "brew_method": "aeropress", "altitude_m": 1600, "varietal": "Catuaí"},
         "Pineapple, rum-soaked raisin and vanilla. Funky in the best way, like a cocktail that forgot it was coffee."),
        ("Moka Blend No. 3", "Barista Lab", "Italy", 76, ["roasted:smoke", "nutty:dark-chocolate", "roasted:toast"], [3, 2, 8, 8, 6, 9],
         {"process": "washed", "roast": "dark", "brew_method": "moka", "varietal": "Blend"},
         "Old-school stovetop: bittersweet chocolate, toast, a wisp of smoke. Needs sugar, does not apologise."),
    ],
    "tea": [
        ("Gyokuro Okumidori", "Sencha Club", "Japan", 94, ["vegetal:seaweed", "vegetal:grass", "sweet:honey"], [6, 2, 2, 6, 8, 7],
         {"tea_type": "green", "water_temp_c": 55, "steep_seconds": 120, "infusions": 4, "harvest": "First flush 2026"},
         "Brothy umami, nori and spring grass, with a sweetness that builds over four infusions."),
        ("Da Hong Pao", "Tējas Nams", "China", 90, ["roasted:toast", "fruity:stone-fruit", "earthy:mineral"], [5, 3, 4, 7, 9, 7],
         {"tea_type": "oolong", "water_temp_c": 95, "steep_seconds": 15, "infusions": 8, "harvest": "Spring 2025"},
         "Charcoal-roasted, then wet rock and ripe apricot. The 'rock rhyme' finish is real."),
        ("Darjeeling Second Flush", "Tējas Nams", "India", 88, ["fruity:cherry", "sweet:maple", "floral:rose"], [5, 5, 4, 5, 7, 6],
         {"tea_type": "black", "water_temp_c": 90, "steep_seconds": 180, "infusions": 1, "harvest": "Summer 2026"},
         "The famous muscatel: grape skin, red cherry and a malty-maple base."),
        ("Silver Needle", "Sencha Club", "China", 86, ["floral:chamomile", "vegetal:hay", "sweet:honey"], [6, 2, 1, 3, 6, 3],
         {"tea_type": "white", "water_temp_c": 80, "steep_seconds": 240, "infusions": 3, "harvest": "Spring 2026"},
         "Barely there and utterly calming. Chamomile, sweet hay, a whisper of honey."),
        ("Shou Pu-erh 2012", "Tējas Nams", "China", 85, ["earthy:forest-floor", "earthy:mushroom", "sweet:brown-sugar"], [5, 1, 3, 9, 8, 8],
         {"tea_type": "puerh", "water_temp_c": 100, "steep_seconds": 10, "infusions": 10, "harvest": "2012 cake"},
         "Deep, dark, forest floor after rain. Brown-sugar sweetness rescues it from pure earth."),
        ("Masala Chai", "Home kitchen", "India", 80, ["spice:cardamom", "spice:cinnamon", "spice:clove"], [8, 2, 3, 7, 6, 8],
         {"tea_type": "black", "water_temp_c": 100, "steep_seconds": 300, "infusions": 1},
         "Assam simmered with cardamom, cinnamon, clove and ginger. Milk, jaggery. Winter in a mug."),
        ("Lavender Earl Grey", "Sencha Club", "Sri Lanka", 78, ["floral:lavender", "fruity:citrus", "sweet:vanilla"], [5, 4, 3, 4, 5, 5],
         {"tea_type": "black", "water_temp_c": 95, "steep_seconds": 210, "infusions": 1},
         "Bergamot and lavender in polite conversation; vanilla keeps it from getting perfumey."),
        ("Ali Shan High Mountain", "Tējas Nams", "Taiwan", 91, ["floral:orange-blossom", "sweet:vanilla", "vegetal:herbal"], [7, 3, 1, 6, 8, 6],
         {"tea_type": "oolong", "water_temp_c": 90, "steep_seconds": 45, "infusions": 6, "harvest": "Winter 2025"},
         "Creamy, orchid-like florals and a buttery mouthfeel. Each pour sweeter than the last."),
    ],
    "chocolate": [
        ("Madagascar Sambirano 72%", "Ingrid Bars", "Madagascar", 93, ["fruity:citrus", "fruity:blueberry", "nutty:cocoa"], [5, 8, 4, 5, 7, 7],
         {"cocoa_percent": 72, "chocolate_type": "dark", "bean": "Trinitario", "texture": "Silky, quick melt"},
         "Raspberry and lemon zest burst before the cocoa arrives. A chocolate that tastes like fruit."),
        ("Piura Porcelana 70%", "Ingrid Bars", "Peru", 91, ["sweet:caramel", "nutty:almond", "fruity:stone-fruit"], [6, 5, 3, 6, 7, 6],
         {"cocoa_percent": 70, "chocolate_type": "dark", "bean": "Criollo", "texture": "Creamy"},
         "Pale beans, gentle caramel, marzipan and apricot. Elegant."),
        ("Smoked Sea Salt 80%", "Laima Craft", "Ghana", 82, ["roasted:smoke", "nutty:dark-chocolate", "earthy:mineral"], [3, 3, 7, 7, 7, 9],
         {"cocoa_percent": 80, "chocolate_type": "dark", "bean": "Forastero", "texture": "Firm snap"},
         "Campfire smoke and flaky salt against bitter cocoa. Pairs worryingly well with Islay whisky."),
        ("Caramelised White", "Laima Craft", "Latvia", 79, ["sweet:caramel", "sweet:vanilla", "nutty:hazelnut"], [9, 1, 1, 7, 5, 5],
         {"cocoa_percent": 32, "chocolate_type": "white", "texture": "Fudgy"},
         "Slow-roasted white chocolate: dulce de leche, toasted hazelnut, vanilla. Dangerous."),
        ("Ecuador Arriba 64% Milk", "Ingrid Bars", "Ecuador", 87, ["floral:jasmine", "sweet:honey", "nutty:cocoa"], [7, 4, 2, 6, 6, 5],
         {"cocoa_percent": 64, "chocolate_type": "milk", "bean": "Nacional", "texture": "Smooth"},
         "Dark-milk with the famous Arriba florals. Jasmine and honey over gentle cocoa."),
        ("Vietnam Ben Tre 78%", "Laima Craft", "Vietnam", 88, ["spice:cinnamon", "fruity:dried-fruit", "spice:black-pepper"], [4, 6, 5, 6, 8, 8],
         {"cocoa_percent": 78, "chocolate_type": "dark", "bean": "Trinitario", "texture": "Dense"},
         "Cinnamon, dried fig and a peppery tingle. Long, warming finish."),
        ("Raw Cacao Nib Bar", "Green Spoon", "Dominican Republic", 74, ["earthy:wet-stone", "vegetal:herbal", "nutty:cocoa"], [2, 5, 8, 4, 5, 7],
         {"cocoa_percent": 85, "chocolate_type": "raw", "texture": "Gritty, rustic"},
         "Unroasted and unapologetic: green, astringent, mineral. Interesting more than delicious."),
        ("Hazelnut Gianduja", "Laima Craft", "Italy", 85, ["nutty:hazelnut", "sweet:brown-sugar", "nutty:cocoa"], [8, 2, 2, 8, 6, 6],
         {"cocoa_percent": 45, "chocolate_type": "milk", "texture": "Melts on contact"},
         "Piedmont hazelnuts ground into milk chocolate. Like the spread, but grown up."),
    ],
    "wine": [
        ("Pinot Noir 'Les Gamets'", "Domaine Rousseau", "France", 92, ["fruity:cherry", "floral:rose", "earthy:forest-floor"], [3, 7, 2, 4, 8, 6],
         {"style": "red", "grape": "Pinot Noir", "vintage": 2021, "abv": "13.0"},
         "Sour cherry, dried rose, a forest floor note that grows in the glass. Weightless but persistent."),
        ("Grüner Veltliner Federspiel", "Weingut Hirsch", "Austria", 88, ["vegetal:herbal", "spice:black-pepper", "fruity:citrus"], [2, 8, 1, 4, 6, 6],
         {"style": "white", "grape": "Grüner Veltliner", "vintage": 2024, "abv": "12.5"},
         "White pepper, lime and fresh herbs. Crunchy and very food-friendly."),
        ("Amber Rkatsiteli Qvevri", "Pheasant's Tears", "Georgia", 90, ["fruity:dried-fruit", "spice:clove", "sweet:honey"], [3, 6, 5, 7, 8, 8],
         {"style": "orange", "grape": "Rkatsiteli", "vintage": 2022, "abv": "12.0"},
         "Six months on skins in clay: dried apricot, black tea tannin, clove and honeycomb."),
        ("Rioja Gran Reserva", "López de Heredia", "Spain", 94, ["earthy:leather", "sweet:vanilla", "roasted:tobacco"], [3, 6, 4, 7, 9, 7],
         {"style": "red", "grape": "Tempranillo", "vintage": 2012, "abv": "13.5"},
         "Leather armchair, cedar box, vanilla and dried strawberry. Time made visible."),
        ("Riesling Kabinett", "Dr. Loosen", "Germany", 89, ["fruity:stone-fruit", "earthy:mineral", "floral:orange-blossom"], [7, 9, 1, 3, 7, 6],
         {"style": "white", "grape": "Riesling", "vintage": 2023, "abv": "8.5"},
         "Slate and white peach, with a sweet-sour tension that keeps you sipping."),
        ("Provence Rosé", "Château Minuty", "France", 80, ["fruity:citrus", "fruity:stone-fruit", "floral:rose"], [3, 6, 1, 3, 4, 4],
         {"style": "rose", "grape": "Grenache", "vintage": 2025, "abv": "12.5"},
         "Pale salmon, grapefruit pith and watermelon. Exactly what a terrace wants."),
        ("Blanc de Blancs Brut", "Pierre Péters", "France", 93, ["roasted:toast", "fruity:citrus", "nutty:almond"], [2, 8, 2, 4, 8, 7],
         {"style": "sparkling", "grape": "Chardonnay", "vintage": 2018, "abv": "12.0"},
         "Brioche and toasted almond under laser-sharp lemon. Fine, persistent bead."),
        ("Malbec Alta Altura", "Catena Zapata", "Argentina", 86, ["fruity:blueberry", "floral:lavender", "nutty:dark-chocolate"], [4, 5, 4, 8, 7, 8],
         {"style": "red", "grape": "Malbec", "vintage": 2020, "abv": "14.0"},
         "Blueberry, violet and dark chocolate. Plush, high-altitude freshness keeps it honest."),
    ],
}

COMMENTS = [
    "Tried this last week — the finish really is that long.",
    "Your notes are spot on. I got more stone fruit than you, though.",
    "Adding this to my list.",
    "Which brew ratio did you use?",
    "Not for me, but beautifully described.",
    "This paired with the Gianduja is unreal.",
    "Bought a second bag immediately.",
    "The radar looks almost identical to my favourite Pinot. Fascinating.",
]


class Command(BaseCommand):
    help = "Seed the journal with demo contributors and tastings."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing tastings and demo users first.")

    def handle(self, *args, reset=False, **options):
        if reset:
            Tasting.objects.all().delete()
            User.objects.filter(username__in=DEMO_USERS).delete()
        elif Tasting.objects.exists():
            self.stdout.write("Journal already has tastings — use --reset to re-seed.")
            return

        rng = random.Random(42)
        users = []
        for name in DEMO_USERS:
            user, created = User.objects.get_or_create(username=name)
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users.append(user)

        now = timezone.now()
        created = 0
        for category, rows in TASTINGS.items():
            for name, producer, origin, score, flavors, profile, details, notes in rows:
                author = rng.choice(users[:3])
                likers = rng.sample(users, rng.randint(0, len(users)))
                commenters = rng.sample(users, rng.randint(0, 3))
                when = now - timezone.timedelta(days=rng.randint(0, 180), hours=rng.randint(0, 23))
                Tasting.objects.create(
                    author=author,
                    category=category,
                    name=name,
                    producer=producer,
                    origin=origin,
                    score=score,
                    notes=notes,
                    flavors=flavors,
                    profile=Profile(**dict(zip(["sweetness", "acidity", "bitterness", "body", "finish", "intensity"], profile))),
                    details=DETAIL_MODELS[category](**details),
                    likes=[ObjectId(str(u.pk)) for u in likers],
                    comments=[
                        Comment(
                            uid=new_comment_id(),
                            author_id=ObjectId(str(u.pk)),
                            author_name=u.username,
                            text=rng.choice(COMMENTS),
                            created_at=when + timezone.timedelta(hours=rng.randint(1, 72)),
                        )
                        for u in commenters
                    ],
                    created_at=when,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created} tastings and {len(users)} contributors (password: {DEMO_PASSWORD})."
        ))
