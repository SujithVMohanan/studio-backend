
"""API views for credit packs, balances, and ledger entries."""

from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.credits.schemas import (
    BalanceSchema,
    CreditPackSchema,
    LedgerEntrySchema,
)
from apps.credits.serializer import (
    BalanceAtQuerySerializer,
    GetLedgerQuerySerializer,
    GrantCreditPackSerializer,
)
from apps.credits.services.credit_service import CreditService
from core.permissions import IsMemberRole, IsStaffRole
from core.responses import ResponseInfo


class GrantCreditPackApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class = GrantCreditPackSerializer

    @swagger_auto_schema(
        request_body=GrantCreditPackSerializer,
        tags=["Credits"],
        operation_summary="Grant credit pack",
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        pack = CreditService.grant_pack(
            actor=request.user,
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.created(
            CreditPackSchema(pack).data,
            message="Credit pack granted successfully.",
        )


class GetBalanceApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated, IsMemberRole]
    serializer_class = BalanceSchema

    @swagger_auto_schema(
        tags=["Credits"],
        operation_summary="My balance and packs",
    )
    def get(self, request, *args, **kwargs):
        balance = CreditService.get_balance(member=request.user)

        return ResponseInfo.ok(
            BalanceSchema(balance).data,
            message="Balance retrieved successfully.",
        )


class GetBalanceAtApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated, IsMemberRole]
    serializer_class = BalanceSchema

    @swagger_auto_schema(
        query_serializer=BalanceAtQuerySerializer,
        tags=["Credits"],
        operation_summary="My balance at a past moment",
    )
    def get(self, request, *args, **kwargs):
        query_serializer = BalanceAtQuerySerializer(
            data=request.query_params,
        )

        if not query_serializer.is_valid():
            return ResponseInfo.validation_error(query_serializer.errors)

        balance = CreditService.get_balance_at(
            member=request.user,
            at=query_serializer.validated_data["at"],
        )

        return ResponseInfo.ok(
            BalanceSchema(balance).data,
            message="Balance retrieved successfully.",
        )


class GetLedgerApiView(generics.ListAPIView):

    permission_classes        = [IsAuthenticated, IsMemberRole]
    serializer_class          = LedgerEntrySchema
    query_serializer_class    = GetLedgerQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetLedgerQuerySerializer,
        tags=["Credits"],
        operation_summary="My credit movements",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        
        query_serializer = self.query_serializer_class(
            data=self.request.query_params,
        )
        query_serializer.is_valid(raise_exception=True)

        return CreditService.list_ledger(
            member=self.request.user,
            validated_data=query_serializer.validated_data,
        )
