from dataclasses import dataclass
from datetime import datetime

from apps.credits.models import CreditPack


@dataclass(frozen=True)
class PackBalance:
    pack:       CreditPack
    remaining:  int
    is_active:  bool
    is_expired: bool


@dataclass(frozen=True)
class BalanceView:
    at:      datetime
    balance: int
    packs:   list[PackBalance]
