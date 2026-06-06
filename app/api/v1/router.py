from fastapi import APIRouter

from app.api.v1 import alerts, audit, auth, backups, dashboard, databases, jobs, kubeconfigs, restores, storages, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(databases.router, prefix="/databases", tags=["databases"])
api_router.include_router(storages.router, prefix="/storages", tags=["storages"])
api_router.include_router(backups.router, tags=["backups"])
api_router.include_router(restores.router, tags=["restore"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(dashboard.router)
api_router.include_router(alerts.router)
api_router.include_router(kubeconfigs.router, prefix="/kubeconfigs", tags=["kubeconfigs"])
