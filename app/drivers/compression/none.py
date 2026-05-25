from pathlib import Path

from app.drivers.compression.base import CompressionDriver


class NoCompressionDriver(CompressionDriver):
    name = "none"
    extension = ""

    def compress(self, source: Path, target: Path | None = None) -> Path:
        return source

    def decompress(self, source: Path, target: Path | None = None) -> Path:
        return source

