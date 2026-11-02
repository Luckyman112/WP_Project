# --- Stage 1: compile SCSS with Sass + PostCSS ---------------------------------
FROM node:24-alpine AS assets
WORKDIR /app
COPY package.json package-lock.json postcss.config.js ./
RUN npm ci --no-audit --no-fund
COPY assets ./assets
RUN npm run build

# --- Stage 2: Django application ------------------------------------------------
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=False
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=assets /app/static/css ./static/css
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home palate && chown -R palate /app
USER palate

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed && gunicorn palate.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
