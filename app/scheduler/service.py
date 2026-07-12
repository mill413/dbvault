from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.core.errors import AppError
from app.models import BackupTask, Job, User
from app.schemas.backups import BackupRunRequest
from app.services.backup_service import create_backup_task, run_backup_task, try_acquire_job_slot

_scheduler: BackgroundScheduler | None = None


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
    if schedule_type in {"ONCE", "ONE_TIME", "ONE-SHOT", "DATE"}:
        if not job.run_at:
            raise ValueError("run_at is required for one-time jobs")
        return DateTrigger(run_date=job.run_at, timezone=job.timezone)
    raise ValueError(f"Unsupported schedule_type: {job.schedule_type}")


def create_scheduler() -> BackgroundScheduler:
    return BackgroundScheduler(timezone="Asia/Shanghai")


def job_has_active_task(db, job: Job) -> bool:
    return (
        db.query(BackupTask)
        .filter(BackupTask.job_id == job.id, BackupTask.status.in_(["PENDING", "RUNNING"]))
        .first()
        is not None
    )


def ensure_job_can_start(db, job: Job) -> None:
    if not job.allow_concurrent and job_has_active_task(db, job):
        raise AppError("JOB_ALREADY_RUNNING", "Job already has a pending or running backup task", status_code=400)


def execute_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job or not job.enabled or job.deleted_at is not None:
            return
        if not job.allow_concurrent:
            if job_has_active_task(db, job):
                job.skipped_count += 1
                db.commit()
                return
        payload = BackupRunRequest(
            database_id=job.database_id,
            storage_id=job.storage_id,
            compression=job.backup_config.get("compression", "zstd"),
            checksum=job.backup_config.get("checksum", ["sha256"]),
            retention=job.retention_policy,
        )
        user = db.get(User, job.created_by) if job.created_by else None
        if not user:
            job.skipped_count += 1
            db.commit()
            return
        task = create_backup_task(db, payload, user, trigger_type="JOB", job_id=job.id)
        if not try_acquire_job_slot(db, job, task):
            job.skipped_count += 1
            db.commit()
            return
        result = run_backup_task(db, task.id)
        job.last_run_at = result.started_at
        job.last_status = result.status
        db.commit()
    finally:
        db.close()


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler()
    return _scheduler


def register_job(job: Job) -> None:
    scheduler = get_scheduler()
    scheduler.add_job(
        execute_job,
        trigger=build_trigger(job),
        args=[job.id],
        id=f"job-{job.id}",
        replace_existing=True,
        max_instances=1,
    )


def remove_job(job_id: int) -> None:
    scheduler = get_scheduler()
    if scheduler.get_job(f"job-{job_id}"):
        scheduler.remove_job(f"job-{job_id}")


def reload_job(job: Job) -> None:
    remove_job(job.id)
    if job.enabled and job.deleted_at is None:
        register_job(job)


def start_scheduler() -> None:
    scheduler = get_scheduler()
    db = SessionLocal()
    try:
        for job in db.query(Job).filter(Job.enabled.is_(True), Job.deleted_at.is_(None)).all():
            register_job(job)
    finally:
        db.close()
    if not scheduler.running:
        scheduler.start()


def shutdown_scheduler() -> None:
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
