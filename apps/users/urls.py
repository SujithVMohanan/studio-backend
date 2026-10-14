from django.urls import path

from apps.users.views import (
    CurrentUserApiView,
    LoginUserApiView,
    LogoutUserApiView,
    RefreshTokenApiView,
    RegisterUserApiView,
)

app_name = "users"

urlpatterns = [
    path("register/", RegisterUserApiView.as_view(), name="register"),
    path("login/", LoginUserApiView.as_view(), name="login"),
    path("refresh/", RefreshTokenApiView.as_view(), name="refresh"),
    path("logout/", LogoutUserApiView.as_view(), name="logout"),
    path("me/", CurrentUserApiView.as_view(), name="me"),
]
