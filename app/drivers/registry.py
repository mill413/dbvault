class DriverRegistry:
    def __init__(self) -> None:
        self._database_drivers: dict[str, type] = {}
        self._storage_drivers: dict[str, type] = {}
        self._compression_drivers: dict[str, type] = {}

    def register_database(self, db_type: str, driver_cls: type) -> None:
        self._database_drivers[db_type.lower()] = driver_cls

    def get_database(self, db_type: str) -> type:
        key = db_type.lower()
        if key not in self._database_drivers:
            raise KeyError(f"Unsupported database driver: {db_type}")
        return self._database_drivers[key]

    def register_storage(self, storage_type: str, driver_cls: type) -> None:
        self._storage_drivers[storage_type.lower()] = driver_cls

    def get_storage(self, storage_type: str) -> type:
        key = storage_type.lower()
        if key not in self._storage_drivers:
            raise KeyError(f"Unsupported storage driver: {storage_type}")
        return self._storage_drivers[key]

    def register_compression(self, compression: str, driver_cls: type) -> None:
        self._compression_drivers[compression.lower()] = driver_cls

    def get_compression(self, compression: str) -> type:
        key = compression.lower()
        if key not in self._compression_drivers:
            raise KeyError(f"Unsupported compression driver: {compression}")
        return self._compression_drivers[key]


registry = DriverRegistry()

