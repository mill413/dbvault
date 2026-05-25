import gzip
import shutil
from pathlib import Path

from app.drivers.compression.base import CompressionDriver


class GzipCompressionDriver(CompressionDriver):
    name = "gzip"
    extension = "gz"

    def compress(self, source: Path, target: Path | None = None) -> Path:
        target = target or source.with_suffix(source.suffix + ".gz")
        with source.open("rb") as src, gzip.open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        return target

    def decompress(self, source: Path, target: Path | None = None) -> Path:
        target = target or source.with_suffix("")
        with gzip.open(source, "rb") as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        return target

