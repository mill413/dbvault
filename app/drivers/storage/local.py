import shutil
from pathlib import Path

from app.core.config import get_settings
from app.drivers.storage.base import StorageDriver


class LocalStorageDriver(StorageDriver):
    storage_type = "local"

    @property
    def root(self) -> Path:
        configured = self.config.get("root_path") or self.config.get("path")
        return Path(configured) if configured else get_settings().local_storage_root

    def _path(self, object_key: str) -> Path:
        root = self.root.resolve()
        target = (root / object_key).resolve()
        if not str(target).startswith(str(root)):
            raise ValueError("Object key escapes storage root")
        return target

    def upload(self, local_path: Path, object_key: str, metadata: dict | None = None) -> dict:
        target = self._path(object_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, target)
        return {"object_key": object_key, "size_bytes": target.stat().st_size, "metadata": metadata or {}}

    def download(self, object_key: str, local_path: Path) -> dict:
        source = self._path(object_key)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, local_path)
        return {"object_key": object_key, "size_bytes": local_path.stat().st_size}

    def exists(self, object_key: str) -> bool:
        return self._path(object_key).exists()

    def delete(self, object_key: str) -> dict:
        path = self._path(object_key)
        if path.exists():
            path.unlink()
        return {"deleted": True}

    def stat(self, object_key: str) -> dict:
        path = self._path(object_key)
        stat = path.stat()
        return {"size_bytes": stat.st_size, "modified_at": stat.st_mtime}

    def test(self) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        return {"ok": self.root.exists(), "message": f"Local storage ready at {self.root}"}

