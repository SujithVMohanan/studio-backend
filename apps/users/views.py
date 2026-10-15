from typing import Any

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.users.models import User
from apps.users.schema import GetUsersApiSchema, LoginResponseSchema
from apps.users.serializer import (
    DeleteUsersSerializer,
    GetUsersQuerySerializer,
    LoginUserSerializer,
    LogoutUserSerializer,
    RefreshTokenSerializer,
    RegisterUserSerializer,
)
from apps.users.services.auth_service import AuthService
from apps.users.services.user_service import UserService
from core.docs import swagger_auto_schema
from core.permissions import IsStaffRole
from core.responses import ResponseInfo
from core.throttles import AuthRateThrottle
from core.utils.request import authenticated_user


def _session_payload(
    tokens: dict[str, str], user: User, schema: type[LoginResponseSchema]
) -> dict[str, Any]:
    return {**tokens, "user": schema(user).data}


class PublicAuthApiView(generics.GenericAPIView[User]):

    permission_classes     = [AllowAny]
    authentication_classes = []
    throttle_classes       = [AuthRateThrottle]

    def get_authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="api"'


class RegisterUserApiView(PublicAuthApiView):

    serializer_class       = RegisterUserSerializer
    response_schema        = LoginResponseSchema

    @swagger_auto_schema(
        request_body=RegisterUserSerializer,
        tags=["auth"],
        operation_summary="User register",
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        tokens, user = UserService.register_user(
            validated_data=serializer.validated_data
        )

        return ResponseInfo.created(
            _session_payload(tokens, user, self.response_schema),
            message="User registered successfully.",
        )


class LoginUserApiView(PublicAuthApiView):

    serializer_class       = LoginUserSerializer
    response_schema        = LoginResponseSchema

    @swagger_auto_schema(
        request_body=LoginUserSerializer,
        tags=["auth"],
        operation_summary="User login",
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        tokens, user = AuthService.login(
            validated_data=serializer.validated_data
        )

        return ResponseInfo.ok(
            _session_payload(tokens, user, self.response_schema),
            message="Login successful",
        )


class RefreshTokenApiView(PublicAuthApiView):

    serializer_class       = RefreshTokenSerializer

    @swagger_auto_schema(
        request_body=RefreshTokenSerializer,
        tags=["auth"],
        operation_summary="Refresh access token",
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        tokens = AuthService.refresh(
            validated_data=serializer.validated_data
        )

        return ResponseInfo.ok(tokens, message="Token refreshed.")


class LogoutUserApiView(generics.GenericAPIView[User]):

    permission_classes = [IsAuthenticated]
    serializer_class   = LogoutUserSerializer

    @swagger_auto_schema(
        request_body=LogoutUserSerializer,
        tags=["auth"],
        operation_summary="User logout",
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        AuthService.logout(
            user=authenticated_user(request),
            access_token=str(request.auth),
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.ok(message="Logout successful")


class CurrentUserApiView(generics.GenericAPIView[User]):

    permission_classes = [IsAuthenticated]
    serializer_class   = LoginResponseSchema

    @swagger_auto_schema(
        tags=["auth"],
        operation_summary="Current user",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return ResponseInfo.ok(
            self.get_serializer(request.user).data,
            message="User retrieved successfully.",
        )


class GetUsersApiView(generics.ListAPIView[User]):

    permission_classes     = [IsAuthenticated, IsStaffRole]
    serializer_class       = GetUsersApiSchema
    query_serializer_class = GetUsersQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetUsersQuerySerializer,
        tags=["Users"],
        operation_summary="Get users",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[User]:
        query = self.query_serializer_class(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return UserService.get_users(
            actor=authenticated_user(self.request),
            validated_data=query.validated_data,
        )


class DeleteUsersApiView(generics.GenericAPIView[User]):

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class   = DeleteUsersSerializer

    @swagger_auto_schema(
        request_body=DeleteUsersSerializer,
        tags=["Users"],
        operation_summary="Delete users",
    )
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        payload = UserService.delete_users(
            actor=authenticated_user(request),
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.ok(payload, message="User(s) deleted successfully.")
