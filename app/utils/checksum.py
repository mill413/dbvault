import hashlib
from pathlib import Path


def file_checksum(path: Path, algorithm: str = "sha256") -> str:
    hash_obj = hashlib.new(algorithm)
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

