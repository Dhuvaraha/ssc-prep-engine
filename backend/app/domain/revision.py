from datetime import date, timedelta


DEFAULT_INTERVALS = (1, 3, 7, 14, 30)


def next_revision_date(
    *,
    today: date,
    successful_reviews: int,
    days_until_exam: int | None = None,
) -> date:
    index = min(successful_reviews, len(DEFAULT_INTERVALS) - 1)
    interval = DEFAULT_INTERVALS[index]

    if days_until_exam is not None and days_until_exam <= 10:
        interval = min(interval, max(1, days_until_exam // 3))

    return today + timedelta(days=interval)
