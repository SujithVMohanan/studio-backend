"""API views for studios and class sessions."""

from typing import Any

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.studios.models import ClassSession, Studio
from apps.studios.schema import ClassSessionSchema, StudioSchema
from apps.studios.serializer import (
    STUDIO_ID_NAMESPACE,
    CreateClassSerializer,
    GetClassesQuerySerializer,
    GetStudiosQuerySerializer,
    StudioSerializer,
)
from apps.studios.services.class_service import ClassService
from apps.studios.services.studio_service import StudioService
from core.docs import swagger_auto_schema
from core.encryption.fields import decode_id_or_404
from core.permissions import IsStaffRole
from core.responses import ResponseInfo
from core.utils.request import authenticated_user


class CreateStudioApiView(generics.GenericAPIView[Studio]):

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class = StudioSerializer

    @swagger_auto_schema(
        request_body=StudioSerializer,
        tags=["Studios"],
        operation_summary="Create studio",
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:

        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        studio = StudioService.create_studio(
            actor=authenticated_user(request),
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.created(
            StudioSchema(studio).data,
            message="Studio created successfully.",
        )


class UpdateStudioApiView(generics.GenericAPIView[Studio]):

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class = StudioSerializer

    @swagger_auto_schema(
        request_body=StudioSerializer,
        tags=["Studios"],
        operation_summary="Update studio",
    )
    def patch(self, request: Request, studio_uid: str, *args: Any, **kwargs: Any) -> Response:
        studio_id = decode_id_or_404(studio_uid, STUDIO_ID_NAMESPACE)
        serializer = self.get_serializer(
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        studio = StudioService.update_studio(
            studio_id=studio_id,
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.ok(
            StudioSchema(studio).data,
            message="Studio updated successfully.",
        )


class GetStudiosApiView(generics.ListAPIView[Studio]):

    permission_classes        = [IsAuthenticated]
    serializer_class          = StudioSchema
    query_serializer_class    = GetStudiosQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetStudiosQuerySerializer,
        tags=["Studios"],
        operation_summary="Get studios",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Studio]:
        serializer = self.query_serializer_class(
            data=self.request.query_params,
        )
        serializer.is_valid(raise_exception=True)

        return StudioService.get_studios(
            validated_data=serializer.validated_data,
        )


class CreateClassApiView(generics.GenericAPIView[ClassSession]):

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class = CreateClassSerializer

    @swagger_auto_schema(
        request_body=CreateClassSerializer,
        tags=["Classes"],
        operation_summary="Schedule class",
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        session = ClassService.schedule_class(
            actor=authenticated_user(request),
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.created(
            ClassSessionSchema(session).data,
            message="Class scheduled successfully.",
        )


class GetClassesApiView(generics.ListAPIView[ClassSession]):

    permission_classes        = [IsAuthenticated]
    serializer_class          = ClassSessionSchema
    query_serializer_class    = GetClassesQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetClassesQuerySerializer,
        tags=["Classes"],
        operation_summary="Browse classes",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[ClassSession]:
        serializer = self.query_serializer_class(
            data=self.request.query_params,
        )
        serializer.is_valid(raise_exception=True)

        return ClassService.browse_classes(
            validated_data=serializer.validated_data,
        )
