from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.models import Job


def build_trigger(job: Job):
    schedule_type = job.schedule_type.upper()
    if schedule_type == "CRON":
        if not job.cron_expr:
            raise ValueError("cron_expr is required for CRON jobs")
        return CronTrigger.from_crontab(job.cron_expr, timezone=job.timezone)
    if schedule_type == "INTERVAL":
        if not job.interval_seconds:
            raise ValueError("interval_seconds is required for INTERVAL jobs")
        return IntervalTrigger(seconds=job.interval_seconds, timezone=job.timezone)
    if schedule_type in {"ONE_TIME", "ONE-SHOT", "DATE"}:
        if not job.run_at:
            raise ValueError("run_at is required for one-time jobs")
        return DateTrigger(run_date=job.run_at, timezone=job.timezone)
    raise ValueError(f"Unsupported schedule_type: {job.schedule_type}")


def create_scheduler() -> BackgroundScheduler:
    return BackgroundScheduler(timezone="Asia/Shanghai")

