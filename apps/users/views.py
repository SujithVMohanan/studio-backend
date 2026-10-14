from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

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
from core.permissions import IsStaffRole
from core.responses import ResponseInfo
from core.throttles import AuthRateThrottle


def _session_payload(tokens: dict, user, schema) -> dict:
    return {**tokens, "user": schema(user).data}


class PublicAuthApiView(generics.GenericAPIView):

    permission_classes     = [AllowAny]
    authentication_classes = []
    throttle_classes       = [AuthRateThrottle]

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'


class RegisterUserApiView(PublicAuthApiView):

    serializer_class       = RegisterUserSerializer
    response_schema        = LoginResponseSchema

    @swagger_auto_schema(
        request_body=RegisterUserSerializer,
        tags=["auth"],
        operation_summary="User register",
    )
    def post(self, request, *args, **kwargs):
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
    def post(self, request, *args, **kwargs):
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
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        tokens = AuthService.refresh(
            validated_data=serializer.validated_data
        )

        return ResponseInfo.ok(tokens, message="Token refreshed.")


class LogoutUserApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class   = LogoutUserSerializer

    @swagger_auto_schema(
        request_body=LogoutUserSerializer,
        tags=["auth"],
        operation_summary="User logout",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        AuthService.logout(
            user=request.user,
            access_token=str(request.auth),
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.ok(message="Logout successful")


class CurrentUserApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class   = LoginResponseSchema

    @swagger_auto_schema(
        tags=["auth"],
        operation_summary="Current user",
    )
    def get(self, request, *args, **kwargs):
        return ResponseInfo.ok(
            self.get_serializer(request.user).data,
            message="User retrieved successfully.",
        )


class GetUsersApiView(generics.ListAPIView):

    permission_classes     = [IsAuthenticated, IsStaffRole]
    serializer_class       = GetUsersApiSchema
    query_serializer_class = GetUsersQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetUsersQuerySerializer,
        tags=["Users"],
        operation_summary="Get users",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        query = self.query_serializer_class(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return UserService.get_users(validated_data=query.validated_data)


class DeleteUsersApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class   = DeleteUsersSerializer

    @swagger_auto_schema(
        request_body=DeleteUsersSerializer,
        tags=["Users"],
        operation_summary="Delete users",
    )
    def delete(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        payload = UserService.delete_users(
            actor=request.user,
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.ok(payload, message="User(s) deleted successfully.")
