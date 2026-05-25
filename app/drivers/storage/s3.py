from pathlib import Path

import boto3
from botocore.client import Config

from app.drivers.storage.base import StorageDriver


class S3StorageDriver(StorageDriver):
    storage_type = "s3"

    def _client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.config.get("endpoint_url"),
            region_name=self.config.get("region") or "us-east-1",
            aws_access_key_id=self.config.get("access_key"),
            aws_secret_access_key=self.config.get("secret_key"),
            use_ssl=self.config.get("use_ssl", True),
            config=Config(s3={"addressing_style": "path" if self.config.get("path_style", True) else "auto"}),
        )

    @property
    def bucket(self) -> str:
        return self.config["bucket"]

    def upload(self, local_path: Path, object_key: str, metadata: dict | None = None) -> dict:
        extra_args = {"Metadata": {k: str(v) for k, v in (metadata or {}).items()}}
        self._client().upload_file(str(local_path), self.bucket, object_key, ExtraArgs=extra_args)
        return {"object_key": object_key, "size_bytes": local_path.stat().st_size, "metadata": metadata or {}}

    def download(self, object_key: str, local_path: Path) -> dict:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._client().download_file(self.bucket, object_key, str(local_path))
        return {"object_key": object_key, "size_bytes": local_path.stat().st_size}

    def exists(self, object_key: str) -> bool:
        try:
            self._client().head_object(Bucket=self.bucket, Key=object_key)
            return True
        except Exception:
            return False

    def delete(self, object_key: str) -> dict:
        self._client().delete_object(Bucket=self.bucket, Key=object_key)
        return {"deleted": True}

    def stat(self, object_key: str) -> dict:
        result = self._client().head_object(Bucket=self.bucket, Key=object_key)
        return {"size_bytes": result["ContentLength"], "metadata": result.get("Metadata", {})}

    def test(self) -> dict:
        self._client().head_bucket(Bucket=self.bucket)
        return {"ok": True, "message": f"S3 bucket {self.bucket} reachable"}


class MinIOStorageDriver(S3StorageDriver):
    storage_type = "minio"

