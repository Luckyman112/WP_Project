from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import CoffeeDetails, Profile, Tasting
from .templatetags.palate import standfirst, verdict

PROFILE = {"sweetness": 7, "acidity": 8, "bitterness": 2, "body": 5, "finish": 7, "intensity": 7}


def payload(**overrides):
    data = {
        "category": "coffee",
        "name": "Guji Natural",
        "producer": "Kalve",
        "origin": "Ethiopia",
        "score": 91,
        "notes": "Blueberry jam. Jasmine on the finish.",
        "flavors": ["fruity:blueberry", "floral:jasmine"],
        "profile": PROFILE,
        "details": {"process": "natural", "roast": "light", "altitude_m": 2100},
        "is_public": True,
    }
    data.update(overrides)
    return data


def make_tasting(author, **overrides):
    fields = {
        "category": "coffee",
        "name": "Seed",
        "score": 85,
        "flavors": ["fruity:cherry"],
        "profile": Profile(**PROFILE),
        "details": CoffeeDetails(roast="light"),
    }
    fields.update(overrides)
    return Tasting.objects.create(author=author, **fields)


class TastingApiTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw-alice-123")
        self.bob = User.objects.create_user("bob", password="pw-bob-123")
        self.client = APIClient()

    # --- create / validate ------------------------------------------------

    def test_anonymous_cannot_create(self):
        response = self.client.post("/api/tastings/", payload(), format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_stores_embedded_documents(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post("/api/tastings/", payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)

        tasting = Tasting.objects.get(pk=response.data["id"])
        self.assertEqual(tasting.author, self.alice)
        self.assertIsInstance(tasting.details, CoffeeDetails)
        self.assertEqual(tasting.details.altitude_m, 2100)
        self.assertEqual(tasting.profile.acidity, 8)
        self.assertEqual(response.data["details"]["process"], "natural")

    def test_rejects_unknown_flavour_and_bad_score(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            "/api/tastings/", payload(flavors=["fruity:durian"], score=120), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("flavors", response.data)
        self.assertIn("score", response.data)

    def test_details_are_validated_per_category(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            "/api/tastings/", payload(category="tea", details={"water_temp_c": 140}), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("water_temp_c", response.data["details"])

    def test_profile_axis_out_of_range(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post(
            "/api/tastings/", payload(profile={**PROFILE, "body": 11}), format="json"
        )
        self.assertEqual(response.status_code, 400)

    # --- permissions & visibility --------------------------------------------

    def test_only_author_can_update_or_delete(self):
        tasting = make_tasting(self.alice)
        url = f"/api/tastings/{tasting.pk}/"

        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.patch(url, {"score": 60}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)

        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.patch(url, {"score": 60}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Tasting.objects.filter(pk=tasting.pk).exists())

    def test_private_tastings_are_hidden_from_others(self):
        private = make_tasting(self.alice, name="Secret", is_public=False)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(f"/api/tastings/{private.pk}/").status_code, 404)
        self.assertEqual(self.client.get("/api/tastings/").data["count"], 0)

        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get("/api/tastings/").data["count"], 1)

    # --- filters ---------------------------------------------------------------

    def test_list_filters(self):
        make_tasting(self.alice, name="Kenya", score=93, flavors=["fruity:cherry"])
        make_tasting(self.alice, name="Pinot", category="wine", details=None, score=88, flavors=["floral:rose"])
        make_tasting(self.bob, name="Moka", score=70, flavors=["roasted:smoke"])

        def names(query):
            return sorted(t["name"] for t in self.client.get(f"/api/tastings/?{query}").data["results"])

        self.assertEqual(names("category=wine"), ["Pinot"])
        self.assertEqual(names("family=fruity"), ["Kenya"])
        self.assertEqual(names("flavor=roasted:smoke"), ["Moka"])
        self.assertEqual(names("min_score=85"), ["Kenya", "Pinot"])
        self.assertEqual(names("author=bob"), ["Moka"])
        self.assertEqual(names("q=pin"), ["Pinot"])

    # --- likes & comments (atomic MongoDB updates) ------------------------------

    def test_like_toggle_is_idempotent(self):
        tasting = make_tasting(self.alice)
        url = f"/api/tastings/{tasting.pk}/like/"
        self.client.force_authenticate(self.bob)

        self.assertEqual(self.client.post(url).data["like_count"], 1)
        self.assertEqual(self.client.post(url).data["like_count"], 1)  # $addToSet
        self.assertEqual(self.client.delete(url).data["like_count"], 0)

    def test_comments_add_list_delete(self):
        tasting = make_tasting(self.alice)
        url = f"/api/tastings/{tasting.pk}/comments/"

        self.assertEqual(self.client.post(url, {"text": "hi"}, format="json").status_code, 403)

        self.client.force_authenticate(self.bob)
        created = self.client.post(url, {"text": "Lovely notes"}, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.post(url, {"text": "   "}, format="json").status_code, 400)

        listed = self.client.get(url).data
        self.assertEqual([c["text"] for c in listed], ["Lovely notes"])

        comment_url = f"{url}{created.data['id']}/"
        self.client.force_authenticate(User.objects.create_user("eve", password="pw-eve-123"))
        self.assertEqual(self.client.delete(comment_url).status_code, 403)
        self.client.force_authenticate(self.alice)  # the tasting's author may moderate
        self.assertEqual(self.client.delete(comment_url).status_code, 204)
        self.assertEqual(self.client.get(url).data, [])

    # --- aggregations ---------------------------------------------------------

    def test_similar_ranks_by_flavour_overlap(self):
        base = make_tasting(self.alice, flavors=["fruity:cherry", "floral:rose"])
        twin = make_tasting(self.bob, name="Twin", category="wine", details=None, flavors=["fruity:cherry", "floral:rose"])
        make_tasting(self.bob, name="Other", flavors=["roasted:smoke"], profile=Profile(**{k: 0 for k in PROFILE}))

        data = self.client.get(f"/api/tastings/{base.pk}/similar/").data
        self.assertEqual(data[0]["id"], str(twin.pk))
        self.assertEqual(data[0]["match_percent"], 100)

        cross = self.client.get(f"/api/tastings/{base.pk}/similar/?cross=1").data
        self.assertTrue(all(t["category"] != "coffee" for t in cross))

    def test_almanac_and_palate(self):
        make_tasting(self.alice, score=80, origin="Kenya", flavors=["fruity:cherry", "spice:clove"])
        make_tasting(self.alice, score=90, origin="Kenya", flavors=["fruity:cherry"])
        make_tasting(self.alice, score=99, is_public=False)

        almanac = self.client.get("/api/almanac/").data
        self.assertEqual(almanac["totals"]["tastings"], 2)
        self.assertEqual(almanac["totals"]["avg_score"], 85.0)
        self.assertEqual(almanac["top_flavors"][0]["id"], "fruity:cherry")
        self.assertEqual(almanac["families"][0], {**almanac["families"][0], "id": "fruity", "count": 2})

        palate = self.client.get("/api/users/alice/palate/").data
        self.assertEqual(palate["count"], 3)
        self.assertEqual(palate["profile"]["acidity"], 8.0)


class PageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("carol", password="pw-carol-123")
        self.tasting = make_tasting(self.user, name="Gesha", notes="Jasmine. Peach.")

    def test_public_pages_render(self):
        for url in ["/", "/journal/", "/compare/", "/almanac/", f"/tastings/{self.tasting.pk}/", "/accounts/carol/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_invalid_object_id_is_404(self):
        self.assertEqual(self.client.get("/tastings/not-an-id/").status_code, 404)

    def test_composer_requires_login_and_ownership(self):
        self.assertEqual(self.client.get("/tastings/new/").status_code, 302)
        other = User.objects.create_user("dave", password="pw-dave-123")
        self.client.force_login(other)
        self.assertEqual(self.client.get(f"/tastings/{self.tasting.pk}/edit/").status_code, 403)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(f"/tastings/{self.tasting.pk}/edit/").status_code, 200)

    def test_signup_logs_in(self):
        response = self.client.post("/accounts/signup/", {
            "username": "newbie", "email": "", "password1": "a-long-Passphrase-77", "password2": "a-long-Passphrase-77",
        })
        self.assertRedirects(response, "/tastings/new/")


class FilterTests(TestCase):
    def test_verdict_and_standfirst(self):
        self.assertEqual(verdict(96), "Transcendent")
        self.assertEqual(verdict(84), "Very good")
        self.assertEqual(standfirst("First line. Second line."), "First line.")
