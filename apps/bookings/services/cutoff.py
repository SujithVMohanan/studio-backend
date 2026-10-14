from datetime import datetime, timedelta
from zoneinfo import ZoneInfo



def is_refundable(
    *,
    starts_at: datetime,
    studio_tz: str,
    cutoff_hours: int,
    now: datetime,
) -> bool:
    
    zone     = ZoneInfo(studio_tz)
    deadline = starts_at.astimezone(zone) - timedelta(hours=cutoff_hours)
    return now.astimezone(zone) <= deadline
