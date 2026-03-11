import os

from a2wsgi import ASGIMiddleware, WSGIMiddleware
from fastapi import FastAPI
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "autism_platform.settings")

django_app = get_wsgi_application()

from autism_platform.api import fastapi_app
from app.main import app as fastapi_site_app
from app.main import on_startup as init_fastapi_site

init_fastapi_site()

main_app = FastAPI(
    title="Autism Assessment Platform",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
main_app.include_router(fastapi_app.router, prefix="/api")
main_app.router.routes.extend(fastapi_site_app.router.routes)


# Let Django keep serving the existing site and routes.
main_app.mount("/", WSGIMiddleware(django_app))

application = ASGIMiddleware(main_app)
