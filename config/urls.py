from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import (
    include,
    path,
    re_path,
)
from django.views.generic import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions


schema_view = get_schema_view(
    openapi.Info(
        title="Studio API",
        default_version="v1",
        description="API documentation for the Studio platform",
        terms_of_service="",
        contact=openapi.Contact(email="sujithvaderiyattil@gmail.com"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="api/docs/", permanent=False)),
    re_path(
        r"^api/",
        include(
            [
                path("users/", include("apps.users.urls")),
                path("studios/", include("apps.studios.urls.studio_urls")),
                path("classes/", include("apps.studios.urls.class_urls")),






                
                re_path(
                    r"^docs/",
                    include(
                        [
                            path(
                                "",
                                schema_view.with_ui("swagger", cache_timeout=0),
                                name="schema-swagger-ui",
                            ),
                            path(
                                "redoc/",
                                schema_view.with_ui("redoc", cache_timeout=0),
                                name="schema-redoc",
                            ),
                            path(
                                "json/",
                                schema_view.without_ui(cache_timeout=0),
                                name="schema-json",
                            ),
                        ]
                    ),
                ),
            ]
        ),
    ),
]


if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
