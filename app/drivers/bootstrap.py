from app.drivers.compression.gzip import GzipCompressionDriver
from app.drivers.compression.none import NoCompressionDriver
from app.drivers.compression.zstd import ZstdCompressionDriver
from app.drivers.database.mysql import MariaDBDriver, MySQLDriver
from app.drivers.database.postgresql import PostgreSQLDriver
from app.drivers.registry import registry
from app.drivers.storage.local import LocalStorageDriver
from app.drivers.storage.s3 import MinIOStorageDriver, S3StorageDriver


def register_builtin_drivers() -> None:
    registry.register_database("mysql", MySQLDriver)
    registry.register_database("mariadb", MariaDBDriver)
    registry.register_database("postgresql", PostgreSQLDriver)
    registry.register_storage("local", LocalStorageDriver)
    registry.register_storage("filesystem", LocalStorageDriver)
    registry.register_storage("s3", S3StorageDriver)
    registry.register_storage("minio", MinIOStorageDriver)
    registry.register_compression("zstd", ZstdCompressionDriver)
    registry.register_compression("gzip", GzipCompressionDriver)
    registry.register_compression("none", NoCompressionDriver)

