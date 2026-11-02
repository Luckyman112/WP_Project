# Palate — a journal of tasting

A dynamic web application for logging coffee, tea, chocolate and wine tastings.
Every tasting is described on **one shared flavour wheel** and a **six-axis
sensory profile**, which lets the app find *kindred tastes across categories* —
an Ethiopian coffee whose closest match turns out to be a German Riesling.

Final project for the *Web Programming* course (TSI).

| | |
|---|---|
| Framework | Django 6.0 + Django REST Framework |
| Database | **MongoDB 8** via the official `django-mongodb-backend` (NoSQL) |
| Styles | SCSS (7-1 architecture) → **Sass** → **PostCSS** (preset-env, Autoprefixer, cssnano) |
| Front-end | Django templates + vanilla ES modules (no framework), hand-built SVG charts |
| Ops | Docker multi-stage build, docker-compose, gunicorn, WhiteNoise |

---

## Quick start

### Option A — Docker (one command)

```bash
docker compose up --build
```

Open <http://localhost:8080>. The database is migrated and seeded automatically.

### Option B — local development

Requirements: Python 3.12+, Node 20+, a MongoDB 6+ server (e.g. `docker run -d -p 27017:27017 mongo:8.0`).

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # adjust if MongoDB is not on localhost

npm install
npm run build                     # SCSS → CSS  (use `npm run watch` while developing)

python manage.py migrate
python manage.py seed             # 32 demo tastings, 4 contributors
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver
```

**Demo accounts:** `mira`, `oskar`, `lena`, `demo` — password `palate-demo-2026`.

### Tests and linting

```bash
python manage.py test             # 17 API and page tests (uses a temporary Mongo database)
npm run lint:css                  # stylelint on the SCSS sources
```

---

## Features — dynamic elements

Each of these updates the page without a reload, talking to the REST API with `fetch()`.

| # | Element | Where | How |
|---|---|---|---|
| 1 | **Interactive flavour wheel** (SVG sunburst, keyboard accessible) | Composer | Click notes to select, click a family to focus |
| 2 | **Live radar chart** redrawn while sliders move | Composer, article, compare | Hand-written SVG with animated transitions |
| 3 | **Category-dependent form fields** | Composer | Fields generated from the model schema per category |
| 4 | **Live search, filter chips, score range, sort** with URL sync | Journal | Debounced `GET /api/tastings/?…`, `history.replaceState` |
| 5 | **Infinite scroll** + "load more" fallback | Journal, profile | `IntersectionObserver` + DRF pagination |
| 6 | **Savour (like) toggle** with optimistic UI and rollback | Article | `POST/DELETE /api/tastings/{id}/like/` |
| 7 | **Letters (comments)** — add, list, delete, live character counter | Article | `/api/tastings/{id}/comments/` |
| 8 | **Kindred tastes** recommendations, same vs. across categories | Article, cover | MongoDB aggregation pipeline |
| 9 | **Side-by-side comparison** — overlaid radars, profile diff, kinship % | Compare | Two parallel API calls |
| 10 | **Almanac statistics** re-computed per category | Almanac | Single `$facet` aggregation |
| 11 | **Draft autosave & restore** | Composer | `localStorage` |
| 12 | **Inline validation** (client + server errors mapped to fields) | Composer | DRF validation errors |
| 13 | **Night edition** theme toggle, toasts, delete confirmation dialog | Everywhere | CSS custom properties, `<dialog>` |

---

## Why MongoDB

A tasting is read as a whole, so it is stored as **one document**:

```js
{
  _id: ObjectId("…"),
  author_id: ObjectId("…"),
  category: "coffee",
  name: "Guji Natural",
  score: 92,
  flavors: ["fruity:blueberry", "floral:jasmine", "sweet:honey"],
  profile:  { sweetness: 7, acidity: 8, bitterness: 2, body: 5, finish: 7, intensity: 7 },
  details:  { process: "natural", roast: "light", altitude_m: 2100, varietal: "Heirloom" },
  likes:    [ObjectId("…"), …],
  comments: [{ uid: "…", author_name: "mira", text: "…", created_at: ISODate("…") }],
  is_public: true, created_at: ISODate("…")
}
```

* **Flexible schema** — `details` is a `PolymorphicEmbeddedModelField`: a coffee
  stores process/roast/altitude, a tea stores water temperature/steep time, a wine
  stores grape/vintage/ABV. In SQL this would need four extra tables or a sparse table.
* **Embedded documents** — profile and comments live inside the tasting; the
  article page is one query, no joins.
* **Atomic array operators** — likes use `$addToSet` / `$pull` (idempotent, no
  race conditions), comments use `$push` / `$pull` (`tastings/services.py`).
* **Aggregation framework** — recommendations rank by Jaccard flavour overlap
  (`$setIntersection`, `$setUnion`) plus profile distance; the Almanac runs one
  `$facet` pipeline with `$group`, `$unwind`, `$bucket`, `$split`.
* **Indexes** on category, score and author (see `Tasting.Meta.indexes`).

---

## REST API

Browsable at `/api/`. Session authentication with CSRF; read access is public,
writes require login, and only the author may change or delete a tasting.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/tastings/` | List (paginated). Filters: `q`, `category`, `family`, `flavor`, `min_score`, `author`, `liked=1`, `sort` |
| POST | `/api/tastings/` | Create |
| GET / PUT / PATCH / DELETE | `/api/tastings/{id}/` | Retrieve / update / delete |
| POST / DELETE | `/api/tastings/{id}/like/` | Savour / un-savour |
| GET / POST | `/api/tastings/{id}/comments/` | List / add letters |
| DELETE | `/api/tastings/{id}/comments/{uid}/` | Delete a letter (its writer or the tasting's author) |
| GET | `/api/tastings/{id}/similar/?cross=1` | Kindred tastes |
| GET | `/api/flavors/` | Flavour wheel taxonomy |
| GET | `/api/almanac/?category=` | Aggregated statistics |
| GET | `/api/users/{username}/palate/` | A contributor's palate fingerprint |

Responses use proper status codes (`201`, `204`, `400` with field errors, `403`, `404`), and the API is throttled.

---

## Styles: Sass + PostCSS pipeline

```
assets/scss/main.scss ──sass──▶ build/main.css ──postcss──▶ static/css/main.css
                                                 ├ postcss-preset-env  (modern CSS fallbacks)
                                                 ├ autoprefixer        (browserslist in package.json)
                                                 └ cssnano             (minification)
```

```
assets/scss/
├── abstracts/   _tokens (maps: themes, categories, breakpoints, spacing)
│                _functions (rem(), space(), step() modular scale, fluid-step() clamp, z())
│                _mixins (mq(), theme-vars(), kicker, drop-cap, dark, %placeholders)
├── base/        reset, theme custom properties, typography, utilities
├── layout/      masthead, sticky nav, page, columns, footer
├── components/  buttons (generated from a map), chips, forms, cards, radar, wheel, toasts, charts
└── pages/       home, journal, article, composer, compare / almanac / profile / auth
```

Techniques used: `@use`/`@forward` modules, maps with `@each` loops to generate
themes, category colours and button variants, custom functions with `math.pow`
and `math.div`, `@content` mixins, placeholder selectors with `@extend`, the
`sass:color` module to generate dark-theme category colours, and CSS counters
for Roman-numeral section numbers.

---

## Best practices applied

* Secrets and environment-specific settings come from environment variables / `.env` (never committed).
* CSRF protection, server-side validation of every field, password validators, ownership checks, private entries.
* User content is inserted with `textContent`, never `innerHTML` (no XSS from the API).
* Semantic HTML, skip link, `aria-*` states, keyboard-operable flavour wheel, `prefers-reduced-motion`, `prefers-color-scheme`.
* Mobile-first responsive layout; fluid typography with `clamp()`.
* Separation of concerns: models / services (Mongo operations) / API / page views / templates / JS modules.
* Automated tests for API, permissions, aggregations and pages; stylelint for SCSS.
* Production build: `DEBUG=False`, gunicorn, hashed & compressed static files (WhiteNoise), non-root Docker user.

---

## Project structure

```
palate/            settings, root URLs, Mongo-aware app configs
tastings/          models, flavour taxonomy, services (Mongo ops), page views, seed command, tests
  api/             serializers, permissions, viewsets, API URLs
accounts/          sign-up, sign-in, contributor pages
templates/         Django templates
assets/scss/       SCSS sources
static/js/         ES modules (lib/ shared, pages/ per page)
mongo_migrations/  migrations for Django contrib apps on MongoDB
```
