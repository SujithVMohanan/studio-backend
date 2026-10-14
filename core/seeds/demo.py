from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction

from apps.credits.services.credit_service import CreditService
from apps.studios.models import ClassSession, Studio
from apps.studios.services.class_service import ClassService
from core.utils import clock

FIXTURE = "demo"
STAFF_EMAIL = "staff@studio.test"

SCHEDULE_DAYS = 3
SOON_CLASS_LEAD = timedelta(hours=2)


@dataclass(frozen=True, slots=True)
class ClassSlot:
    at: time
    duration_minutes: int
    spots: int
    credit_cost: int


@dataclass(frozen=True, slots=True)
class PackGrant:
    credits: int
    valid_days: int


DAILY_SLOTS = (
    ClassSlot(at=time(7, 0), duration_minutes=60, spots=10, credit_cost=1),
    ClassSlot(at=time(18, 0), duration_minutes=45, spots=2, credit_cost=2),
)

SOON_SLOT = ClassSlot(at=time(0, 0), duration_minutes=60, spots=5, credit_cost=1)

MEMBER_PACKS = {
    "member.a@studio.test": (PackGrant(credits=3, valid_days=7), PackGrant(credits=10, valid_days=30)),
    "member.b@studio.test": (PackGrant(credits=10, valid_days=30),),
    "member.c@studio.test": (PackGrant(credits=2, valid_days=30),),
    "member.d@studio.test": (PackGrant(credits=5, valid_days=30),),
}


@dataclass(slots=True)
class SeedReport:
    classes_created: int = 0
    packs_granted: int = 0


@transaction.atomic
def seed_demo(*, now: datetime | None = None) -> SeedReport:
    current_time = now if now is not None else clock.now()
    report = SeedReport()

    call_command("loaddata", FIXTURE, verbosity=0)

    staff = get_user_model().objects.get(email=STAFF_EMAIL)

    for studio in Studio.objects.order_by("id"):
        report.classes_created += _seed_classes(studio=studio, actor=staff, now=current_time)

    report.packs_granted = _seed_packs(actor=staff, now=current_time)
    return report


def _seed_classes(*, studio: Studio, actor, now: datetime) -> int:
    zone = studio.zone
    local_today = now.astimezone(zone).date()
    created = 0

    for day_offset in range(1, SCHEDULE_DAYS + 1):
        day = local_today + timedelta(days=day_offset)
        for slot in DAILY_SLOTS:
            starts_at = datetime.combine(day, slot.at, tzinfo=zone)
            if ClassSession.objects.filter(studio=studio, starts_at=starts_at).exists():
                continue
            _schedule(studio=studio, actor=actor, slot=slot, starts_at=starts_at, now=now)
            created += 1

    soon_starts_at = (now + SOON_CLASS_LEAD).replace(second=0, microsecond=0)
    has_soon_class = ClassSession.objects.filter(
        studio=studio,
        starts_at__gt=now,
        starts_at__lte=now + timedelta(hours=studio.cancellation_cutoff_hours),
    ).exists()
    if not has_soon_class:
        _schedule(studio=studio, actor=actor, slot=SOON_SLOT, starts_at=soon_starts_at, now=now)
        created += 1

    return created


def _schedule(*, studio: Studio, actor, slot: ClassSlot, starts_at: datetime, now: datetime) -> None:
    ClassService.schedule_class(
        actor=actor,
        validated_data={
            "studio_uid": studio.id,
            "starts_at": starts_at,
            "duration_minutes": slot.duration_minutes,
            "spots": slot.spots,
            "credit_cost": slot.credit_cost,
        },
        now=now,
    )


def _seed_packs(*, actor, now: datetime) -> int:
    User = get_user_model()
    today = clock.utc_today(now)
    granted = 0

    members = User.objects.filter(email__in=MEMBER_PACKS, role=User.Role.MEMBER)
    for member in members:
        if member.credit_packs.exists():
            continue
        for grant in MEMBER_PACKS[member.email]:
            CreditService.grant_pack(
                actor=actor,
                validated_data={
                    "member_uid": member.id,
                    "credits": grant.credits,
                    "granted_on": today,
                    "expires_on": today + timedelta(days=grant.valid_days),
                },
                now=now,
            )
            granted += 1

    return granted
