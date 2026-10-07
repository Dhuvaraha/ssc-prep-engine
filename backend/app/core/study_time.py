from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


SSC_TIMEZONE = ZoneInfo("Asia/Kolkata")


def current_study_date() -> date:
    return datetime.now(SSC_TIMEZONE).date()


def utc_naive_to_study_date(value: datetime) -> date:
    return value.replace(tzinfo=timezone.utc).astimezone(SSC_TIMEZONE).date()
