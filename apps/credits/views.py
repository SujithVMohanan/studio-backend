"""API views for credit packs, balances, and ledger entries."""

from typing import Any

from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.credits.models import CreditLedger, CreditPack
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
from core.docs import swagger_auto_schema
from core.permissions import IsMemberRole, IsStaffRole
from core.responses import ResponseInfo
from core.utils.request import authenticated_user


class GrantCreditPackApiView(generics.GenericAPIView[CreditPack]):

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class = GrantCreditPackSerializer

    @swagger_auto_schema(
        request_body=GrantCreditPackSerializer,
        tags=["Credits"],
        operation_summary="Grant credit pack",
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        pack = CreditService.grant_pack(
            actor=authenticated_user(request),
            validated_data=serializer.validated_data,
        )

        return ResponseInfo.created(
            CreditPackSchema(pack).data,
            message="Credit pack granted successfully.",
        )


class GetBalanceApiView(generics.GenericAPIView[Any]):

    permission_classes = [IsAuthenticated, IsMemberRole]
    serializer_class = BalanceSchema

    @swagger_auto_schema(
        tags=["Credits"],
        operation_summary="My balance and packs",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        balance = CreditService.get_balance(member=authenticated_user(request))

        return ResponseInfo.ok(
            BalanceSchema(balance).data,
            message="Balance retrieved successfully.",
        )


class GetBalanceAtApiView(generics.GenericAPIView[Any]):

    permission_classes = [IsAuthenticated, IsMemberRole]
    serializer_class = BalanceSchema

    @swagger_auto_schema(
        query_serializer=BalanceAtQuerySerializer,
        tags=["Credits"],
        operation_summary="My balance at a past moment",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        query_serializer = BalanceAtQuerySerializer(
            data=request.query_params,
        )

        if not query_serializer.is_valid():
            return ResponseInfo.validation_error(query_serializer.errors)

        balance = CreditService.get_balance_at(
            member=authenticated_user(request),
            at=query_serializer.validated_data["at"],
        )

        return ResponseInfo.ok(
            BalanceSchema(balance).data,
            message="Balance retrieved successfully.",
        )


class GetLedgerApiView(generics.ListAPIView[CreditLedger]):

    permission_classes        = [IsAuthenticated, IsMemberRole]
    serializer_class          = LedgerEntrySchema
    query_serializer_class    = GetLedgerQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetLedgerQuerySerializer,
        tags=["Credits"],
        operation_summary="My credit movements",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[CreditLedger]:

        query_serializer = self.query_serializer_class(
            data=self.request.query_params,
        )
        query_serializer.is_valid(raise_exception=True)

        return CreditService.list_ledger(
            member=authenticated_user(self.request),
            validated_data=query_serializer.validated_data,
        )
