from django.urls import path

from apps.credits.views import GetBalanceApiView, GetBalanceAtApiView, GetLedgerApiView, GrantCreditPackApiView

app_name = "credits"

urlpatterns = [
    path("grant-credit-pack/", GrantCreditPackApiView.as_view(), name="grant-credit-pack"),
    path("get-balance/", GetBalanceApiView.as_view(), name="get-balance"),
    path("get-balance-at/", GetBalanceAtApiView.as_view(), name="get-balance-at"),
    path("get-ledger/", GetLedgerApiView.as_view(), name="get-ledger"),
]