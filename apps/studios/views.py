
"""API views for studios and class sessions."""

from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

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
from core.encryption.fields import decode_id_or_404
from core.responses import ResponseInfo


class CreateStudioApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated,]
    serializer_class = StudioSerializer

    @swagger_auto_schema(
        request_body=StudioSerializer,
        tags=["Studios"],
        operation_summary="Create studio",
    )
    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        studio = StudioService.create_studio(
            actor=request.user,
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.created(
            StudioSchema(studio).data,
            message="Studio created successfully.",
        )


class UpdateStudioApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated,]
    serializer_class = StudioSerializer

    @swagger_auto_schema(
        request_body=StudioSerializer,
        tags=["Studios"],
        operation_summary="Update studio",
    )
    def patch(self, request, studio_uid: str, *args, **kwargs):
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


class GetStudiosApiView(generics.ListAPIView):

    permission_classes        = [IsAuthenticated]
    serializer_class          = StudioSchema
    query_serializer_class    = GetStudiosQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetStudiosQuerySerializer,
        tags=["Studios"],
        operation_summary="Get studios",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        serializer = self.query_serializer_class(
            data=self.request.query_params,
        )
        serializer.is_valid(raise_exception=True)

        return StudioService.get_studios(
            validated_data=serializer.validated_data,
        )


class CreateClassApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated,]
    serializer_class = CreateClassSerializer

    @swagger_auto_schema(
        request_body=CreateClassSerializer,
        tags=["Classes"],
        operation_summary="Schedule class",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        session = ClassService.schedule_class(
            actor=request.user,
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.created(
            ClassSessionSchema(session).data,
            message="Class scheduled successfully.",
        )


class GetClassesApiView(generics.ListAPIView):

    permission_classes        = [IsAuthenticated]
    serializer_class          = ClassSessionSchema
    query_serializer_class    = GetClassesQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetClassesQuerySerializer,
        tags=["Classes"],
        operation_summary="Browse classes",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        serializer = self.query_serializer_class(
            data=self.request.query_params,
        )
        serializer.is_valid(raise_exception=True)

        return ClassService.browse_classes(
            validated_data=serializer.validated_data,
        )
