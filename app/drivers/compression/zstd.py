from pathlib import Path

import zstandard as zstd

from app.drivers.compression.base import CompressionDriver


class ZstdCompressionDriver(CompressionDriver):
    name = "zstd"
    extension = "zst"

    def compress(self, source: Path, target: Path | None = None) -> Path:
        target = target or source.with_suffix(source.suffix + ".zst")
        compressor = zstd.ZstdCompressor(level=3, threads=-1)
        with source.open("rb") as src, target.open("wb") as dst:
            compressor.copy_stream(src, dst)
        return target

    def decompress(self, source: Path, target: Path | None = None) -> Path:
        target = target or source.with_suffix("")
        decompressor = zstd.ZstdDecompressor()
        with source.open("rb") as src, target.open("wb") as dst:
            decompressor.copy_stream(src, dst)
        return target

