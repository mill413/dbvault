from pathlib import Path


class CompressionDriver:
    name = "base"
    extension = ""

    def compress(self, source: Path, target: Path | None = None) -> Path:
        raise NotImplementedError

    def decompress(self, source: Path, target: Path | None = None) -> Path:
        raise NotImplementedError

