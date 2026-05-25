from pathlib import Path


class StorageDriver:
    storage_type = "base"

    def __init__(self, config: dict) -> None:
        self.config = config

    def upload(self, local_path: Path, object_key: str, metadata: dict | None = None) -> dict:
        raise NotImplementedError

    def download(self, object_key: str, local_path: Path) -> dict:
        raise NotImplementedError

    def exists(self, object_key: str) -> bool:
        raise NotImplementedError

    def delete(self, object_key: str) -> dict:
        raise NotImplementedError

    def stat(self, object_key: str) -> dict:
        raise NotImplementedError

    def test(self) -> dict:
        raise NotImplementedError

