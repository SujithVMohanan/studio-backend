from django.urls import path

from apps.studios.views import (
    CreateStudioApiView,
    GetStudiosApiView,
    UpdateStudioApiView,
)

app_name = "studios"

urlpatterns = [
    path("create-studio/", CreateStudioApiView.as_view(), name="create-studio"),
    path(
        "update-studio/<str:studio_uid>/",
        UpdateStudioApiView.as_view(),
        name="update-studio",
    ),
    path("get-studios/", GetStudiosApiView.as_view(), name="get-studios"),
]
